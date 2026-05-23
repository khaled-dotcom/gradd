# Deploy EmpowerWork to swedencentral (allowed on Azure for Students @ EUI)
# Prerequisites: az login, Docker optional (uses az acr build)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$LOCATION = "swedencentral"
$RESOURCE_GROUP = "rg-empowerwork"

# Load or create deploy ids
$StateFile = Join-Path $Root "azure-deploy-state.json"
$s = $null
if (Test-Path $StateFile) {
    $s = Get-Content $StateFile -Raw | ConvertFrom-Json
    $PREFIX = $s.prefix
} else {
    $PREFIX = "ewsw$(Get-Random -Maximum 99999)"
}

$STORAGE_NAME = "${PREFIX}st"
$MYSQL_SERVER = "${PREFIX}db"
$ACR_NAME = "${PREFIX}acr"
$API_APP = "${PREFIX}api"
$PLAN_NAME = "${PREFIX}plan"
$ADMIN_USER = "ewadmin"
if ($s -and $s.adminPass) { $ADMIN_PASS = $s.adminPass } else {
    $ADMIN_PASS = (-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 20 | ForEach-Object { [char]$_ })) + "!aA1"
}

Write-Host "=== EmpowerWork Azure ($LOCATION) prefix=$PREFIX ===" -ForegroundColor Cyan

az group create -n $RESOURCE_GROUP -l $LOCATION --output none 2>$null

if (-not (az storage account show -g $RESOURCE_GROUP -n $STORAGE_NAME 2>$null)) {
    Write-Host "Storage: $STORAGE_NAME"
    az storage account create -g $RESOURCE_GROUP -n $STORAGE_NAME -l $LOCATION --sku Standard_LRS --output none
}
$key = az storage account keys list -g $RESOURCE_GROUP -n $STORAGE_NAME --query "[0].value" -o tsv
az storage container create --account-name $STORAGE_NAME --name empowerwork --public-access blob --account-key $key --output none 2>$null
$STORAGE_CONN = az storage account show-connection-string -g $RESOURCE_GROUP -n $STORAGE_NAME --query connectionString -o tsv

if (-not (az mysql flexible-server show -g $RESOURCE_GROUP -n $MYSQL_SERVER 2>$null)) {
    Write-Host "MySQL: $MYSQL_SERVER"
    az mysql flexible-server create -g $RESOURCE_GROUP -n $MYSQL_SERVER -l $LOCATION `
        --sku-name Standard_B1ms --tier Burstable --storage-size 32 --version 8.0.21 `
        --admin-user $ADMIN_USER --admin-password $ADMIN_PASS --public-access 0.0.0.0 --yes --output none
    az mysql flexible-server db create -g $RESOURCE_GROUP --server-name $MYSQL_SERVER --database-name rag_jobs --output none
}
$DB_HOST = az mysql flexible-server show -g $RESOURCE_GROUP -n $MYSQL_SERVER --query fullyQualifiedDomainName -o tsv
$DB_USER = "${ADMIN_USER}@${MYSQL_SERVER}"

if (-not (az acr show -n $ACR_NAME 2>$null)) {
    Write-Host "ACR: $ACR_NAME"
    az acr create -g $RESOURCE_GROUP -n $ACR_NAME --sku Basic --admin-enabled true --output none
}
$ACR_LOGIN = az acr show -n $ACR_NAME --query loginServer -o tsv

Write-Host "Building image in ACR (cloud build)..."
az acr build --registry $ACR_NAME --image empowerwork-api:latest . --output none

if (-not (az appservice plan show -g $RESOURCE_GROUP -n $PLAN_NAME 2>$null)) {
    Write-Host "App Service plan: $PLAN_NAME"
    az appservice plan create -g $RESOURCE_GROUP -n $PLAN_NAME --is-linux --sku B1 -l $LOCATION --output none
}

if (-not (az webapp show -g $RESOURCE_GROUP -n $API_APP 2>$null)) {
    Write-Host "Web App: $API_APP"
    az webapp create -g $RESOURCE_GROUP -p $PLAN_NAME -n $API_APP --deployment-container-image-name "mcr.microsoft.com/appsvc/staticsite:latest" --output none
}

$ACR_USER = az acr credential show -n $ACR_NAME --query username -o tsv
$ACR_PASS = az acr credential show -n $ACR_NAME --query "passwords[0].value" -o tsv

az webapp config container set -g $RESOURCE_GROUP -n $API_APP `
    --docker-custom-image-name "${ACR_LOGIN}/empowerwork-api:latest" `
    --docker-registry-server-url "https://${ACR_LOGIN}" `
    --docker-registry-server-user $ACR_USER `
    --docker-registry-server-password $ACR_PASS --output none

$groq = $env:GROQ_API_KEY
if (-not $groq) { $groq = "REPLACE_ME" }
$openai = $env:OPENAI_API_KEY
if (-not $openai) { $openai = "REPLACE_ME" }

az webapp config appsettings set -g $RESOURCE_GROUP -n $API_APP --settings `
    WEBSITES_PORT=8000 `
    WEBSITES_ENABLE_APP_SERVICE_STORAGE=true `
    EVENTS_ENABLED=false `
    DB_HOST=$DB_HOST `
    DB_USER=$DB_USER `
    DB_PASS=$ADMIN_PASS `
    DB_NAME=rag_jobs `
    DB_SSL=true `
    GROQ_API_KEY=$groq `
    OPENAI_API_KEY=$openai `
    GROQ_MODEL=llama-3.1-8b-instant `
    CHROMA_DIR=/home/site/wwwroot/.chroma `
    AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONN `
    AZURE_STORAGE_CONTAINER=empowerwork `
    AZURE_SPARK_REPORT_BLOB=reports/latest.json `
    IDS_ENABLED=false `
    CORS_ORIGINS=* `
    --output none

az webapp config set -g $RESOURCE_GROUP -n $API_APP --always-on true --output none
az webapp restart -g $RESOURCE_GROUP -n $API_APP --output none

$API_URL = "https://${API_APP}.azurewebsites.net"
$state = @{
    prefix = $PREFIX
    location = $LOCATION
    resourceGroup = $RESOURCE_GROUP
    storageName = $STORAGE_NAME
    mysqlServer = $MYSQL_SERVER
    acrName = $ACR_NAME
    apiApp = $API_APP
    apiUrl = $API_URL
    dbHost = $DB_HOST
    dbUser = $DB_USER
    dbPass = $ADMIN_PASS
    adminPass = $ADMIN_PASS
    storageConnectionString = $STORAGE_CONN
} | ConvertTo-Json
$state | Set-Content $StateFile -Encoding UTF8

@"
# Copy to .env for seeding
DB_HOST=$DB_HOST
DB_USER=$DB_USER
DB_PASS=$ADMIN_PASS
DB_NAME=rag_jobs
DB_SSL=true
GROQ_API_KEY=$groq
OPENAI_API_KEY=$openai
AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONN
"@ | Set-Content (Join-Path $Root "azure-deploy-output.env") -Encoding UTF8

Write-Host "`n=== DONE ===" -ForegroundColor Green
Write-Host "API:      $API_URL"
Write-Host "Health:   $API_URL/health"
Write-Host "Secrets:  azure-deploy-output.env"
Write-Host "State:    azure-deploy-state.json"
if ($groq -eq "REPLACE_ME") { Write-Host "Set GROQ_API_KEY in Portal -> App Service -> Configuration" -ForegroundColor Yellow }
Write-Host "Seed DB:  .\scripts\azure-seed-db.ps1"
Write-Host "SWA:      VITE_API_URL=$API_URL  VITE_EVENTS_ENABLED=false"
