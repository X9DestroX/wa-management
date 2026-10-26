import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json; charset=utf-8",
};

const allowedRoles = new Set(["RH", "Gestionnaire", "Administrateur"]);

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: corsHeaders });
}

function cleanString(value: unknown, max = 120): string {
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return response({ error: "Méthode non autorisée." }, 405);

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL");

    // Current Supabase runtimes expose named key maps; legacy variables remain as fallbacks.
    function namedKey(variable: string): string | undefined {
      const raw = Deno.env.get(variable);
      if (!raw) return undefined;
      try {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object" && typeof parsed.default === "string") {
          return parsed.default;
        }
      } catch {
        // Not JSON: support a legacy single-key value.
      }
      return raw;
    }

    const publicKey =
      namedKey("SUPABASE_PUBLISHABLE_KEYS") ??
      Deno.env.get("SUPABASE_PUBLISHABLE_KEY") ??
      Deno.env.get("SUPABASE_ANON_KEY");

    const serviceRoleKey =
      namedKey("SUPABASE_SECRET_KEYS") ??
      Deno.env.get("SUPABASE_SECRET_KEY") ??
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

    if (!supabaseUrl || !publicKey || !serviceRoleKey) {
      console.error("Configuration des secrets Supabase incomplète.");
      return response({ error: "Configuration serveur incomplète. Vérifiez les secrets Supabase de la fonction." }, 500);
    }

    const authHeader = req.headers.get("Authorization") ?? "";
    const tokenMatch = authHeader.match(/^Bearer\s+(.+)$/i);
    if (!tokenMatch) return response({ error: "Connexion requise." }, 401);

    const token = tokenMatch[1];
    const authClient = createClient(supabaseUrl, publicKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const { data: authData, error: authError } = await authClient.auth.getUser(token);
    if (authError || !authData.user) return response({ error: "Session expirée ou invalide. Reconnectez-vous." }, 401);

    const adminClient = createClient(supabaseUrl, serviceRoleKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });

    const { data: actor, error: actorError } = await adminClient
      .from("profiles")
      .select("id, username, full_name, role")
      .eq("id", authData.user.id)
      .maybeSingle();

    if (actorError || !actor || actor.role !== "Administrateur") {
      return response({ error: "Accès réservé à l’administrateur." }, 403);
    }

    let body: Record<string, unknown>;
    try {
      body = await req.json();
    } catch {
      return response({ error: "Corps de requête JSON invalide." }, 400);
    }

    const action = cleanString(body.action, 20).toLowerCase();

    if (action === "list") {
      const [{ data: profiles, error: profilesError }, { data: usersData, error: usersError }] = await Promise.all([
        adminClient.from("profiles").select("id, username, full_name, role, created_at").order("username"),
        adminClient.auth.admin.listUsers({ page: 1, perPage: 1000 }),
      ]);
      if (profilesError || usersError) {
        console.error("Erreur de liste", profilesError?.message, usersError?.message);
        return response({ error: "Impossible de charger la liste des utilisateurs." }, 500);
      }
      const emails = new Map((usersData.users ?? []).map((u) => [u.id, u.email ?? ""]));
      return response({
        users: (profiles ?? []).map((p) => ({
          id: p.id,
          email: emails.get(p.id) ?? "",
          username: p.username,
          full_name: p.full_name,
          role: p.role,
          created_at: p.created_at,
        })),
      });
    }

    if (action === "create") {
      const email = cleanString(body.email, 254).toLowerCase();
      const username = cleanString(body.username, 64);
      const fullName = cleanString(body.full_name, 120);
      const password = typeof body.password === "string" ? body.password : "";
      const role = cleanString(body.role, 32);

      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return response({ error: "Adresse e-mail invalide." }, 400);
      if (!username || !/^[A-Za-z0-9._-]{2,64}$/.test(username)) return response({ error: "Nom d’utilisateur invalide (2–64 caractères : lettres, chiffres, point, tiret ou souligné)." }, 400);
      if (password.length < 12) return response({ error: "Le mot de passe doit contenir au moins 12 caractères." }, 400);
      if (!allowedRoles.has(role)) return response({ error: "Rôle invalide." }, 400);

      const { data: duplicate, error: duplicateError } = await adminClient.from("profiles").select("id").eq("username", username).maybeSingle();
      if (duplicateError) return response({ error: "Impossible de vérifier le nom d’utilisateur." }, 500);
      if (duplicate) return response({ error: "Ce nom d’utilisateur existe déjà." }, 409);

      const { data: created, error: createError } = await adminClient.auth.admin.createUser({
        email,
        password,
        email_confirm: true,
        user_metadata: { username, full_name: fullName },
      });
      if (createError || !created.user) {
        return response({ error: createError?.message ?? "Création de l’utilisateur impossible." }, 400);
      }

      const { error: profileError } = await adminClient.from("profiles").update({
        username,
        full_name: fullName,
        role,
      }).eq("id", created.user.id);
      if (profileError) {
        console.error("Profil créé mais mise à jour échouée", created.user.id, profileError.message);
        return response({ error: "Le compte Auth a été créé, mais son profil n’a pas pu être finalisé. Ne recréez pas ce compte ; vérifiez la table profiles." }, 500);
      }

      await adminClient.from("audit").insert({
        username: actor.username,
        action: "admin-users:create",
        details: { target_id: created.user.id, email, username, role },
      });

      return response({ ok: true, user_id: created.user.id, message: "Utilisateur créé." }, 201);
    }

    if (action === "update") {
      const id = cleanString(body.id, 64);
      if (!id) return response({ error: "Identifiant utilisateur obligatoire." }, 400);

      const { data: target, error: targetError } = await adminClient.from("profiles")
        .select("id, username, full_name, role")
        .eq("id", id)
        .maybeSingle();
      if (targetError || !target) return response({ error: "Utilisateur introuvable." }, 404);

      const username = cleanString(body.username ?? target.username, 64);
      const fullName = cleanString(body.full_name ?? target.full_name, 120);
      const role = cleanString(body.role ?? target.role, 32);
      const email = cleanString(body.email, 254).toLowerCase();
      const password = typeof body.password === "string" ? body.password : "";

      if (!username || !/^[A-Za-z0-9._-]{2,64}$/.test(username)) return response({ error: "Nom d’utilisateur invalide." }, 400);
      if (!allowedRoles.has(role)) return response({ error: "Rôle invalide." }, 400);
      if (password && password.length < 12) return response({ error: "Le nouveau mot de passe doit contenir au moins 12 caractères." }, 400);
      if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return response({ error: "Adresse e-mail invalide." }, 400);
      if (id === actor.id && role !== "Administrateur") return response({ error: "Vous ne pouvez pas retirer votre propre rôle Administrateur." }, 400);

      const { data: duplicate, error: duplicateError } = await adminClient.from("profiles")
        .select("id").eq("username", username).neq("id", id).maybeSingle();
      if (duplicateError) return response({ error: "Impossible de vérifier le nom d’utilisateur." }, 500);
      if (duplicate) return response({ error: "Ce nom d’utilisateur est déjà utilisé." }, 409);

      if (target.role === "Administrateur" && role !== "Administrateur") {
        const { count, error: countError } = await adminClient.from("profiles")
          .select("id", { count: "exact", head: true }).eq("role", "Administrateur");
        if (countError) return response({ error: "Impossible de vérifier les administrateurs existants." }, 500);
        if ((count ?? 0) <= 1) return response({ error: "Impossible de retirer le rôle du dernier Administrateur." }, 400);
      }

      const authChanges: Record<string, unknown> = { user_metadata: { username, full_name: fullName } };
      if (email) {
        authChanges.email = email;
        authChanges.email_confirm = true;
      }
      if (password) authChanges.password = password;

      const { error: authUpdateError } = await adminClient.auth.admin.updateUserById(id, authChanges);
      if (authUpdateError) return response({ error: authUpdateError.message }, 400);

      const { error: profileUpdateError } = await adminClient.from("profiles")
        .update({ username, full_name: fullName, role })
        .eq("id", id);
      if (profileUpdateError) {
        console.error("Compte Auth mis à jour mais profil en échec", id, profileUpdateError.message);
        return response({ error: "Le compte d’authentification a été modifié, mais le profil n’a pas été finalisé. Vérifiez la table profiles." }, 500);
      }

      await adminClient.from("audit").insert({
        username: actor.username,
        action: "admin-users:update",
        details: { target_id: id, username, role, email_changed: Boolean(email), password_changed: Boolean(password) },
      });
      return response({ ok: true, message: "Utilisateur mis à jour." });
    }

    if (action === "delete") {
      const id = cleanString(body.id, 64);
      if (!id) return response({ error: "Identifiant utilisateur obligatoire." }, 400);
      if (id === actor.id) return response({ error: "Vous ne pouvez pas supprimer votre propre compte." }, 400);

      const { data: target, error: targetError } = await adminClient.from("profiles")
        .select("id, username, role").eq("id", id).maybeSingle();
      if (targetError || !target) return response({ error: "Utilisateur introuvable." }, 404);

      if (target.role === "Administrateur") {
        const { count, error: countError } = await adminClient.from("profiles")
          .select("id", { count: "exact", head: true }).eq("role", "Administrateur");
        if (countError) return response({ error: "Impossible de vérifier les administrateurs existants." }, 500);
        if ((count ?? 0) <= 1) return response({ error: "Impossible de supprimer le dernier Administrateur." }, 400);
      }

      const { error: deleteError } = await adminClient.auth.admin.deleteUser(id);
      if (deleteError) return response({ error: deleteError.message }, 400);

      await adminClient.from("audit").insert({
        username: actor.username,
        action: "admin-users:delete",
        details: { target_id: id, username: target.username, role: target.role },
      });
      return response({ ok: true, message: "Utilisateur supprimé." });
    }

    return response({ error: "Action inconnue. Actions autorisées : list, create, update, delete." }, 400);
  } catch (error) {
    console.error("Erreur admin-users inattendue", error);
    return response({ error: "Erreur serveur inattendue." }, 500);
  }
});
