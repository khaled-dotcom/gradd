# Provision EmpowerWork on Azure (student account)
# Run from project root after:  az login
#
#   .\scripts\azure-provision.ps1
# Optional env overrides:
#   $env:AZURE_LOCATION = "westeurope"
#   $env:AZURE_RESOURCE_GROUP = "rg-empowerwork"
#   $env:SKIP_MYSQL = "1"   # use existing Aiven DB instead

param(
    [string]$ResourceGroup = $(if ($env:AZURE_RESOURCE_GROUP) { $env:AZURE_RESOURCE_GROUP } else { "rg-empowerwork" }),
    [string]$Location = $(if ($env:AZURE_LOCATION) { $env:AZURE_LOCATION } else { "swedencentral" }),
    [string]$NamePrefix = $(if ($env:AZURE_NAME_PREFIX) { $env:AZURE_NAME_PREFIX } else { "empowerwork" }),
    [switch]$SkipMysql = ([bool]($env:SKIP_MYSQL -eq "1"))
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Require-Az {
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        throw "Azure CLI not found. Install: https://learn.microsoft.com/cli/azure/install-azure-cli-windows"
    }
    $acct = az account show 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Not logged in. Run:  az login"
    }
    Write-Host "Subscription:" (az account show --query name -o tsv) -ForegroundColor Green
}

function New-RandomPassword {
    -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ }) + "!aA1"
}

Require-Az

$ApiApp = "${NamePrefix}-api"
$StorageName = ($NamePrefix + "store").ToLower().Replace("-", "").Substring(0, [Math]::Min(24, ($NamePrefix + "store").Length))
if ($StorageName.Length -lt 3) { $StorageName = "ewstore$(Get-Random -Maximum 9999)" }
$MysqlServer = "${NamePrefix}-mysql"
$AdminUser = "ewadmin"
$AdminPass = New-RandomPassword
$PlanName = "${NamePrefix}-plan"
$AcrName = ($NamePrefix + "acr").ToLower().Replace("-", "").Substring(0, [Math]::Min(50, ($NamePrefix + "acr").Length))

Write-Host "`n=== Creating resource group: $ResourceGroup ($Location) ===" -ForegroundColor Cyan
az group create --name $ResourceGroup --location $Location --output none

Write-Host "=== Storage account: $StorageName ===" -ForegroundColor Cyan
az storage account create `
    --resource-group $ResourceGroup `
    --name $StorageName `
    --location $Location `
    --sku Standard_LRS `
    --kind StorageV2 `
    --output none

az storage container create `
    --account-name $StorageName `
    --name empowerwork `
    --public-access blob `
    --auth-mode login `
    --output none 2>$null
if ($LASTEXITCODE -ne 0) {
    $key = az storage account keys list -g $ResourceGroup -n $StorageName --query "[0].value" -o tsv
    az storage container create --account-name $StorageName --name empowerwork --public-access blob --account-key $key --output none
}

$StorageConn = az storage account show-connection-string -g $ResourceGroup -n $StorageName --query connectionString -o tsv

if (-not $SkipMysql) {
    Write-Host "=== MySQL Flexible Server: $MysqlServer (B1ms) ===" -ForegroundColor Cyan
    az mysql flexible-server create `
        --resource-group $ResourceGroup `
        --name $MysqlServer `
        --location $Location `
        --sku-name Standard_B1ms `
        --tier Burstable `
        --storage-size 32 `
        --version 8.0.21 `
        --admin-user $AdminUser `
        --admin-password $AdminPass `
        --public-access 0.0.0.0 `
        --yes `
        --output none

    az mysql flexible-server db create `
        --resource-group $ResourceGroup `
        --server-name $MysqlServer `
        --database-name rag_jobs `
        --output none

    $DbHost = az mysql flexible-server show -g $ResourceGroup -n $MysqlServer --query fullyQualifiedDomainName -o tsv
    $DbUser = "${AdminUser}@${MysqlServer}"
} else {
    Write-Host "=== SKIP_MYSQL=1 — configure DB_* manually (e.g. Aiven) ===" -ForegroundColor Yellow
    $DbHost = "YOUR_DB_HOST"
    $DbUser = "YOUR_DB_USER"
    $AdminPass = "YOUR_DB_PASS"
}

Write-Host "=== Azure Container Registry: $AcrName ===" -ForegroundColor Cyan
az acr create --resource-group $ResourceGroup --name $AcrName --sku Basic --admin-enabled true --output none
$AcrLoginServer = az acr show -n $AcrName --query loginServer -o tsv
$AcrUser = az acr credential show -n $AcrName --query username -o tsv
$AcrPass = az acr credential show -n $AcrName --query "passwords[0].value" -o tsv

Write-Host "=== App Service Plan (B1 Linux) ===" -ForegroundColor Cyan
az appservice plan create -g $ResourceGroup -n $PlanName --is-linux --sku B1 --output none

Write-Host "=== Web App: $ApiApp ===" -ForegroundColor Cyan
az webapp create -g $ResourceGroup -p $PlanName -n $ApiApp --deployment-container-image-name "mcr.microsoft.com/appsvc/staticsite:latest" --output none

az webapp config container set -g $ResourceGroup -n $ApiApp `
    --docker-custom-image-name "${AcrLoginServer}/empowerwork-api:latest" `
    --docker-registry-server-url "https://${AcrLoginServer}" `
    --docker-registry-server-user $AcrUser `
    --docker-registry-server-password $AcrPass `
    --output none

az webapp config appsettings set -g $ResourceGroup -n $ApiApp --settings `
    WEBSITES_PORT=8000 `
    WEBSITES_ENABLE_APP_SERVICE_STORAGE=true `
    EVENTS_ENABLED=false `
    DB_HOST=$DbHost `
    DB_USER=$DbUser `
    DB_PASS=$AdminPass `
    DB_NAME=rag_jobs `
    DB_SSL=true `
    GROQ_MODEL=llama-3.1-8b-instant `
    CHROMA_DIR=/home/site/wwwroot/.chroma `
    AZURE_STORAGE_CONNECTION_STRING=$StorageConn `
    AZURE_STORAGE_CONTAINER=empowerwork `
    AZURE_SPARK_REPORT_BLOB=reports/latest.json `
    IDS_ENABLED=false `
    CORS_ORIGINS=* `
    --output none

az webapp config set -g $ResourceGroup -n $ApiApp --always-on true --output none

Write-Host "=== Building and pushing Docker image ===" -ForegroundColor Cyan
az acr login --name $AcrName
docker build -t "${AcrLoginServer}/empowerwork-api:latest" .
docker push "${AcrLoginServer}/empowerwork-api:latest"
az webapp restart -g $ResourceGroup -n $ApiApp --output none

$ApiUrl = "https://${ApiApp}.azurewebsites.net"
$OutFile = Join-Path $Root "azure-deploy-output.env"

@"
# Generated $(Get-Date -Format o) — add GROQ_API_KEY and OPENAI_API_KEY in Portal
RESOURCE_GROUP=$ResourceGroup
API_URL=$ApiUrl
STORAGE_ACCOUNT=$StorageName
STORAGE_CONNECTION_STRING=$StorageConn
ACR_NAME=$AcrName
ACR_LOGIN_SERVER=$AcrLoginServer
DB_HOST=$DbHost
DB_USER=$DbUser
DB_PASS=$AdminPass
DB_NAME=rag_jobs
DB_SSL=true

# Frontend Static Web Apps (create in Portal — GitHub):
#   App location: frontend | Output: dist
#   VITE_API_URL=$ApiUrl
#   VITE_EVENTS_ENABLED=false

# After Portal adds API keys, seed DB:
#   copy azure-deploy-output.env .env  (add GROQ_API_KEY)
#   .\scripts\azure-seed-db.ps1
"@ | Set-Content -Path $OutFile -Encoding UTF8

Write-Host "`n=== DONE ===" -ForegroundColor Green
Write-Host "API:     $ApiUrl"
Write-Host "Health:  $ApiUrl/health"
Write-Host "Secrets: $OutFile"
Write-Host "`nNext: Portal -> App Service -> Configuration -> add GROQ_API_KEY, OPENAI_API_KEY"
Write-Host "      Create Static Web App (frontend) with VITE_API_URL=$ApiUrl"
Write-Host "      .\scripts\azure-seed-db.ps1"
