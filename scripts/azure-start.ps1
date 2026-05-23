# Resume EmpowerWork on Azure after azure-stop.ps1
# Run: .\scripts\azure-start.ps1
$ErrorActionPreference = "Stop"
$rg = "rg-empowerwork"

Write-Host "Starting MySQL (wait ~2-3 min before using DB)..." -ForegroundColor Cyan
az mysql flexible-server start -g $rg -n ewsw55166db -o none
Write-Host "  Started ewsw55166db"

try {
    $ip = (Invoke-RestMethod -Uri "https://api.ipify.org?format=json" -TimeoutSec 10).ip
    $rule = "dev-$($ip.Replace('.','-'))"
    az mysql flexible-server firewall-rule create -g $rg -n ewsw55166db `
        --rule-name $rule --start-ip-address $ip --end-ip-address $ip -o none 2>$null
    Write-Host "  MySQL firewall: allowed $ip" -ForegroundColor DarkGray
} catch {
    Write-Host "  MySQL firewall: could not add current IP (add manually in Portal)" -ForegroundColor Yellow
}

Write-Host "Syncing Azure Blob settings for CV/profile uploads..." -ForegroundColor Cyan
$st = "ewsw55166st"
$conn = az storage account show-connection-string -g $rg -n $st --query connectionString -o tsv
az webapp config appsettings set -g $rg -n ewsw55166api --settings `
    "AZURE_STORAGE_CONNECTION_STRING=$conn" `
    AZURE_STORAGE_CONTAINER=empowerwork `
    -o none
Write-Host "  Blob storage wired for ewsw55166api"

Write-Host "Starting web apps..." -ForegroundColor Cyan
foreach ($app in @("ewsw55166api", "empowerwork-api-ew55166")) {
    if (az webapp show -g $rg -n $app 2>$null) {
        az webapp start -g $rg -n $app -o none
        Write-Host "  Started $app"
    }
}

Write-Host "`nURLs:" -ForegroundColor Green
Write-Host "  API:      https://ewsw55166api.azurewebsites.net"
Write-Host "  Frontend: https://ewsw55166st.z1.web.core.windows.net/"
Write-Host "Wait 1-2 minutes, then open /health and the site."
