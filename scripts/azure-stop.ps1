# Pause EmpowerWork on Azure (keep resources for later).
# Run: .\scripts\azure-stop.ps1
$ErrorActionPreference = "Stop"
$rg = "rg-empowerwork"

Write-Host "Stopping web apps..." -ForegroundColor Cyan
foreach ($app in @("ewsw55166api", "empowerwork-api-ew55166")) {
    if (az webapp show -g $rg -n $app 2>$null) {
        az webapp stop -g $rg -n $app -o none
        Write-Host "  Stopped $app"
    }
}

Write-Host "Stopping MySQL..." -ForegroundColor Cyan
az mysql flexible-server stop -g $rg -n ewsw55166db -o none
Write-Host "  Stopped ewsw55166db"

Write-Host "`nDone. Storage/ACR/plan may still incur small charges." -ForegroundColor Green
Write-Host "To start again: .\scripts\azure-start.ps1"
