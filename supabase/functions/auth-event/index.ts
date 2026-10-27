import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json; charset=utf-8",
};

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: corsHeaders });
}
function namedKey(variable: string): string | undefined {
  const raw = Deno.env.get(variable);
  if (!raw) return undefined;
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && typeof parsed.default === "string") return parsed.default;
  } catch { /* legacy variable may be a plain string */ }
  return raw;
}
function jwtClaims(token: string): Record<string, unknown> {
  try {
    const part = token.split(".")[1];
    if (!part) return {};
    const normalized = part.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(normalized + "=".repeat((4 - normalized.length % 4) % 4)));
  } catch { return {}; }
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return response({ error: "Méthode non autorisée." }, 405);

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const publicKey = namedKey("SUPABASE_PUBLISHABLE_KEYS") ?? Deno.env.get("SUPABASE_PUBLISHABLE_KEY") ?? Deno.env.get("SUPABASE_ANON_KEY");
    const secretKey = namedKey("SUPABASE_SECRET_KEYS") ?? Deno.env.get("SUPABASE_SECRET_KEY") ?? Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!supabaseUrl || !publicKey || !secretKey) {
      console.error("Configuration des secrets Supabase incomplète.");
      return response({ error: "Configuration serveur incomplète." }, 500);
    }

    const authHeader = req.headers.get("Authorization") ?? "";
    const tokenMatch = authHeader.match(/^Bearer\s+(.+)$/i);
    if (!tokenMatch) return response({ error: "Connexion requise." }, 401);
    const token = tokenMatch[1];

    const authClient = createClient(supabaseUrl, publicKey, { auth: { persistSession: false, autoRefreshToken: false } });
    const { data: authResult, error: authError } = await authClient.auth.getUser(token);
    if (authError || !authResult.user) return response({ error: "Session invalide ou expirée." }, 401);

    let body: Record<string, unknown>;
    try { body = await req.json(); } catch { return response({ error: "Corps JSON invalide." }, 400); }
    const event = String(body.event ?? "").trim().toLowerCase();
    if (!(["login", "logout"] as string[]).includes(event)) return response({ error: "Seuls les événements login et logout sont acceptés." }, 400);

    const admin = createClient(supabaseUrl, secretKey, { auth: { persistSession: false, autoRefreshToken: false } });
    const { data: profile, error: profileError } = await admin.from("profiles")
      .select("id, username, full_name, role").eq("id", authResult.user.id).maybeSingle();
    if (profileError || !profile) return response({ error: "Profil employé introuvable." }, 403);

    // session_id is read only after Supabase has validated the bearer token.
    const claims = jwtClaims(token);
    const sessionId = typeof claims.session_id === "string" ? claims.session_id : null;
    const op = event === "login" ? "LOGIN" : "LOGOUT";
    const { error: insertError } = await admin.from("audit").insert({
      username: profile.username,
      action: event === "login" ? "Connexion réussie" : "Déconnexion",
      details: { source: "application", user_agent: req.headers.get("user-agent") ?? "" },
      actor_id: profile.id,
      actor_email: authResult.user.email ?? null,
      actor_role: profile.role,
      entity_table: "auth",
      entity_id: profile.id,
      operation: op,
      auth_session_id: sessionId,
    });

    if (insertError) {
      // Repeated invocation for the same Auth session should not create duplicate login/logout rows.
      if (insertError.code === "23505") return response({ ok: true, duplicate: true });
      console.error("Écriture du journal d'authentification impossible", insertError.message);
      return response({ error: "Impossible d’enregistrer l’événement de connexion." }, 500);
    }
    return response({ ok: true });
  } catch (error) {
    console.error("Erreur inattendue auth-event", error);
    return response({ error: "Erreur serveur inattendue." }, 500);
  }
});
