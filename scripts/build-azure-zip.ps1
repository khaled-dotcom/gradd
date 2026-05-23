# Build deploy.zip for Azure App Service (Oryx pip build; tar = forward slashes).
# Set on Web App: SCM_DO_BUILD_DURING_DEPLOYMENT=true, COMPRESS_DESTINATION_DIR=false
param(
    [string]$OutZip = "deploy.zip"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$staging = Join-Path $root "deploy_staging"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null

Copy-Item requirements.txt, runtime.txt -Destination $staging
$ewapp = Join-Path $staging "ewapp"
New-Item -ItemType Directory -Path $ewapp | Out-Null
robocopy (Join-Path $root "backend\src") $ewapp /E /XD __pycache__ /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed: $LASTEXITCODE" }

Get-ChildItem $staging -Recurse -Include *.py | ForEach-Object {
    $text = [IO.File]::ReadAllText($_.FullName)
    $updated = $text -replace 'backend\.src\.', 'ewapp.' -replace 'backend\.src', 'ewapp'
    if ($updated -ne $text) { [IO.File]::WriteAllText($_.FullName, $updated) }
}

$appPy = @'
"""Azure App Service entrypoint."""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from ewapp.main import app  # noqa: E402
'@ -replace "`r`n", "`n"
[IO.File]::WriteAllText((Join-Path $staging "app.py"), $appPy, [Text.UTF8Encoding]::new($false))

$zipPath = Join-Path $root $OutZip
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Push-Location $staging
tar -a -cf $zipPath *
Pop-Location
Remove-Item $staging -Recurse -Force

Write-Host "Created $zipPath ($((Get-Item $zipPath).Length) bytes)"
