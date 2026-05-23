# Build frontend and upload to Azure Storage static website (works in swedencentral).
param(
    [string]$ResourceGroup = "rg-empowerwork",
    [string]$StorageAccount = "ewsw55166st",
    [string]$ApiUrl = "https://ewsw55166api.azurewebsites.net"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"

Write-Host "=== Frontend -> Storage static site ($StorageAccount) ===" -ForegroundColor Cyan

$conn = az storage account show-connection-string -g $ResourceGroup -n $StorageAccount --query connectionString -o tsv

az storage blob service-properties update `
    --connection-string $conn `
    --static-website `
    --index-document index.html `
    --404-document index.html `
    --output none

$env:VITE_API_URL = $ApiUrl
$env:VITE_EVENTS_ENABLED = "false"

Push-Location $Frontend
if (-not (Test-Path node_modules)) {
    Write-Host "npm ci..."
    npm ci
}
Write-Host "npm run build..."
npm run build
Pop-Location

$dist = Join-Path $Frontend "dist"
if (-not (Test-Path (Join-Path $dist "index.html"))) {
    throw "Build failed: $dist/index.html missing"
}

Write-Host "Uploading dist -> `$web..."
az storage blob upload-batch `
    --connection-string $conn `
    --destination '$web' `
    --source $dist `
    --overwrite `
    --output none

$webUrl = az storage account show -g $ResourceGroup -n $StorageAccount `
    --query "primaryEndpoints.web" -o tsv

Write-Host "`nFrontend URL: $webUrl" -ForegroundColor Green
Write-Host "API URL:      $ApiUrl"
