// W-A Systeme de Gestion — secure username sign-in.
// The desktop client sends only the publishable key. This Edge Function resolves
// usernames privately and verifies the password with Supabase Auth.
// New sb_secret_* / sb_publishable_* keys are sent in apikey only. Legacy JWT
// service_role keys also receive Authorization: Bearer for backward compatibility.

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Content-Type": "application/json; charset=utf-8",
};

function response(body: unknown, status = 200, extraHeaders: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, ...extraHeaders },
  });
}

function namedKey(variable: string, legacyVariable?: string): string | undefined {
  const raw = Deno.env.get(variable);
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        if (typeof parsed.default === "string") return parsed.default;
        const first = Object.values(parsed).find((value) => typeof value === "string");
        if (typeof first === "string") return first;
      }
    } catch {
      // Some older/local deployments expose a single raw key.
    }
    return raw;
  }
  return legacyVariable ? Deno.env.get(legacyVariable) ?? undefined : undefined;
}

function isLegacyJwt(value: string): boolean {
  return value.split(".").length === 3;
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

class SupabaseRequestError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function supabaseFetch(
  baseUrl: string,
  path: string,
  apiKey: string,
  method = "GET",
  payload?: unknown,
  adminKey = false,
): Promise<any> {
  const headers: Record<string, string> = {
    apikey: apiKey,
    Accept: "application/json",
  };
  if (payload !== undefined) headers["Content-Type"] = "application/json";
  // Legacy JWT service_role keys need their bearer header. New sb_secret_* keys
  // are opaque API keys and must remain in apikey only.
  if (adminKey && isLegacyJwt(apiKey)) headers.Authorization = `Bearer ${apiKey}`;

  let result: Response;
  try {
    result = await fetch(`${baseUrl}${path}`, {
      method,
      headers,
      body: payload === undefined ? undefined : JSON.stringify(payload),
    });
  } catch (error) {
    console.error("Supabase network request failed:", error);
    throw new SupabaseRequestError("Supabase est momentanément inaccessible.", 503);
  }

  const text = await result.text();
  let data: any = null;
  if (text) {
    try { data = JSON.parse(text); }
    catch { data = { message: text.slice(0, 500) }; }
  }
  if (!result.ok) {
    const message = String(data?.message ?? data?.msg ?? data?.error_description ?? data?.error ?? "Erreur Supabase.");
    throw new SupabaseRequestError(message, result.status);
  }
  return data;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method === "GET") {
    // Harmless deployment check. Does not expose project IDs, emails, or secrets.
    return response({ ok: true, service: "username-login", version: "1.7.9.1" });
  }
  if (req.method !== "POST") return response({ error: "Méthode non autorisée." }, 405);

  try {
    const supabaseUrl = (Deno.env.get("SUPABASE_URL") ?? "").replace(/\/+$/, "");
    const publishableKey = namedKey("SUPABASE_PUBLISHABLE_KEYS", "SUPABASE_PUBLISHABLE_KEY")
      ?? Deno.env.get("SUPABASE_ANON_KEY")
      ?? undefined;
    const secretKey = namedKey("SUPABASE_SECRET_KEYS", "SUPABASE_SECRET_KEY")
      ?? Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")
      ?? undefined;

    if (!supabaseUrl || !publishableKey || !secretKey) {
      console.error("Username login: required Supabase environment variables are missing.");
      return response({ error: "Service de connexion indisponible. Vérifiez les clés intégrées aux Edge Functions Supabase." }, 503);
    }

    let body: Record<string, unknown>;
    try { body = await req.json(); }
    catch { return response({ error: "Requête invalide." }, 400); }

    const username = typeof body.username === "string" ? body.username.trim() : "";
    const password = typeof body.password === "string" ? body.password : "";
    if (!/^[A-Za-z0-9._-]{2,64}$/.test(username) || !password) {
      return response({ error: "Nom d’utilisateur ou mot de passe incorrect." }, 401);
    }

    const normalizedUsername = username.toLowerCase();
    const identifierHash = await sha256Hex(normalizedUsername);

    // Consume a login attempt atomically; the SQL function is service-role only.
    let limitRows: any;
    try {
      limitRows = await supabaseFetch(
        supabaseUrl,
        "/rest/v1/rpc/consume_username_login_attempt",
        secretKey,
        "POST",
        { p_identifier_hash: identifierHash },
        true,
      );
    } catch (error) {
      console.error("Username login rate-limit check failed:", error);
      return response({ error: "Configuration de connexion incomplète. Vérifiez que la migration SQL 0007 est exécutée et que username-login est déployée." }, 503);
    }
    const limit = Array.isArray(limitRows) ? limitRows[0] : limitRows;
    if (!limit?.allowed) {
      const retry = Math.max(1, Number(limit?.retry_after_seconds ?? 900));
      return response(
        { error: "Trop de tentatives de connexion. Réessayez dans 15 minutes." },
        429,
        { "Retry-After": String(retry) },
      );
    }

    // Read matching profile IDs only. The email remains inside this trusted function.
    let profiles: any[];
    try {
      const query = new URLSearchParams({ select: "id,username", limit: "2000" });
      profiles = await supabaseFetch(
        supabaseUrl,
        `/rest/v1/profiles?${query.toString()}`,
        secretKey,
        "GET",
        undefined,
        true,
      ) ?? [];
    } catch (error) {
      console.error("Username profile lookup failed:", error);
      return response({ error: "Impossible de rechercher ce compte. Vérifiez les autorisations du service de connexion." }, 503);
    }

    const profile = profiles.find((row: { id?: string; username?: string }) =>
      String(row.username ?? "").toLowerCase() === normalizedUsername,
    );
    if (!profile?.id) return response({ error: "Nom d’utilisateur ou mot de passe incorrect." }, 401);

    // Look up the email via Auth Admin API. Never return it during a failed login.
    let authUser: any;
    try {
      const authUserResponse = await supabaseFetch(
        supabaseUrl,
        `/auth/v1/admin/users/${encodeURIComponent(profile.id)}`,
        secretKey,
        "GET",
        undefined,
        true,
      );
      authUser = authUserResponse?.user ?? authUserResponse;
    } catch (error) {
      console.error("Auth user lookup failed for profile ID:", profile.id, error);
      return response({ error: "Impossible de vérifier ce compte. Vérifiez la fonction username-login et ses clés Supabase." }, 503);
    }
    const email = typeof authUser?.email === "string" ? authUser.email : "";
    if (!email) return response({ error: "Nom d’utilisateur ou mot de passe incorrect." }, 401);

    // Password verification is performed by Supabase Auth using the public key.
    // No service-role key and no user email is sent from the desktop application.
    let signInData: any;
    try {
      signInData = await supabaseFetch(
        supabaseUrl,
        "/auth/v1/token?grant_type=password",
        publishableKey,
        "POST",
        { email, password },
      );
    } catch (error) {
      if (error instanceof SupabaseRequestError && error.status === 400 ||
          error instanceof SupabaseRequestError && error.status === 401) {
        return response({ error: "Nom d’utilisateur ou mot de passe incorrect." }, 401);
      }
      console.error("Supabase Auth sign-in failed:", error);
      return response({ error: "Le service d’authentification Supabase est temporairement indisponible." }, 503);
    }

    if (!signInData?.access_token || !signInData?.user) {
      return response({ error: "Réponse de connexion Supabase invalide." }, 502);
    }

    // Reset the counter after a successful password check. Failure to clean up must
    // not block a valid login.
    try {
      await supabaseFetch(
        supabaseUrl,
        "/rest/v1/rpc/reset_username_login_attempts",
        secretKey,
        "POST",
        { p_identifier_hash: identifierHash },
        true,
      );
    } catch (error) {
      console.error("Could not reset username login attempts:", error);
    }

    return response({
      access_token: signInData.access_token,
      refresh_token: signInData.refresh_token,
      expires_in: signInData.expires_in,
      token_type: signInData.token_type,
      user: signInData.user,
    });
  } catch (error) {
    console.error("Unexpected username login error:", error);
    return response({ error: "Erreur de connexion inattendue. Réessayez ou contactez l’administrateur." }, 500);
  }
});
