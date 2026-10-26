$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "W-A Systeme de Gestion - Configuration Cloud Supabase" -ForegroundColor Cyan
Write-Host "Cette configuration sera enregistree uniquement sur ce PC."
Write-Host "Utilisez la cle Publishable/anon, jamais la cle Secret/service-role."
Write-Host ""

$projectUrl = (Read-Host "URL du projet Supabase (ex: https://xxxx.supabase.co)").Trim().TrimEnd("/")
if ($projectUrl -notmatch '^https://[a-zA-Z0-9-]+\.supabase\.co$') {
    Write-Host "URL invalide. Elle doit ressembler a https://xxxx.supabase.co" -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

$publishableKey = (Read-Host "Cle API Publishable (sb_publishable_... ou ancienne cle anon)").Trim()
if ([string]::IsNullOrWhiteSpace($publishableKey)) {
    Write-Host "Cle vide. Configuration annulee." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}
if ($publishableKey.StartsWith("sb_secret_") -or $publishableKey.StartsWith("sb_service_role_")) {
    Write-Host "ERREUR : cette cle est privee. Utilisez une cle Publishable/anon." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}
# Refuser aussi l'ancienne cle JWT anon/service_role si son role indique service_role.
if ($publishableKey.Count -ge 1 -and $publishableKey -match '^eyJ[^.]+\.([^.]+)\.') {
    try {
        $payload = $Matches[1].Replace('-', '+').Replace('_', '/')
        while (($payload.Length % 4) -ne 0) { $payload += '=' }
        $claims = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload)) | ConvertFrom-Json
        if ($claims.role -eq "service_role" -or $claims.role -eq "supabase_admin") {
            Write-Host "ERREUR : cle service_role detectee. Utilisez la cle Publishable/anon." -ForegroundColor Red
            Read-Host "Appuyez sur Entree pour fermer"
            exit 1
        }
    } catch {
        # If this is not a decodable JWT, the server-side configuration check will validate it.
    }
}

$dataDir = Join-Path $env:USERPROFILE "WA_Manager_System"
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
$configPath = Join-Path $dataDir "cloud_config.json"
$config = [ordered]@{
    enabled = $true
    supabase_url = $projectUrl
    publishable_key = $publishableKey
}
$json = $config | ConvertTo-Json -Depth 4
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($configPath, $json, $utf8NoBom)

Write-Host ""
Write-Host "Configuration cloud enregistree :" -ForegroundColor Green
Write-Host $configPath
Write-Host "Relancez W-A Systeme de Gestion pour activer le mode Cloud."
Write-Host "Ne transmettez pas ce fichier : il contient la cle publique et l'URL du projet."
Read-Host "Appuyez sur Entree pour fermer"
