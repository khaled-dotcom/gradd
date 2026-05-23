# Copy DB settings from azure-deploy-output.env into .env for local seed/migrations.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $Root "azure-deploy-output.env"
$dst = Join-Path $Root ".env"

if (-not (Test-Path $src)) { throw "Missing $src" }

$map = @{}
Get-Content $src | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $k, $v = $_ -split '=', 2
    $map[$k.Trim()] = $v.Trim()
}

$keys = @('DB_HOST','DB_USER','DB_PASS','DB_NAME','DB_SSL','GROQ_API_KEY','OPENAI_API_KEY','GROQ_MODEL','FRONTEND_URL')
$lines = @()
if (Test-Path $dst) {
    Get-Content $dst | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -notmatch '=') { $lines += $_; return }
        $k = ($_ -split '=', 2)[0].Trim()
        if ($keys -contains $k) { return }
        $lines += $_
    }
}
foreach ($k in $keys) {
    if ($map.ContainsKey($k) -and $map[$k]) {
        $lines += "$k=$($map[$k])"
    }
}
if (-not ($lines | Where-Object { $_ -match '^GROQ_MODEL=' })) {
    $lines += "GROQ_MODEL=llama-3.1-8b-instant"
}
$lines | Set-Content -Path $dst -Encoding UTF8
Write-Host "Updated $dst (DB_* from azure-deploy-output.env)"
