param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$ReleaseDir = Join-Path $RootDir "release"
$PackageDir = Join-Path $ReleaseDir "smart-home-demo"
$ZipPath = Join-Path $ReleaseDir "smart-home-demo.zip"
$BackendPython = Join-Path $BackendDir ".venv\Scripts\python.exe"

function Write-Step {
    param([string]$Message)
    Write-Host "[package-demo] $Message"
}

function Require-Path {
    param(
        [string]$Path,
        [string]$Message
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        throw $Message
    }
}

Require-Path $BackendPython "Backend virtual environment not found. Run .\start.ps1 once before packaging."
Require-Path (Join-Path $FrontendDir "package.json") "frontend/package.json was not found."

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

if (-not $SkipTests) {
    Write-Step "running backend tests"
    Push-Location -LiteralPath $BackendDir
    try {
        & $BackendPython -m pytest
    } finally {
        Pop-Location
    }
}

Write-Step "building frontend"
Push-Location -LiteralPath $FrontendDir
try {
    & npm.cmd run build
} finally {
    Pop-Location
}

Write-Step "ensuring PyInstaller is available"
& $BackendPython -m pip install pyinstaller

Write-Step "building backend executable"
$PyInstallerDist = Join-Path $ReleaseDir "pyinstaller-dist"
$PyInstallerBuild = Join-Path $ReleaseDir "pyinstaller-build"
$PyInstallerSpec = Join-Path $ReleaseDir "pyinstaller-spec"
Remove-Item -LiteralPath $PyInstallerDist, $PyInstallerBuild, $PyInstallerSpec -Recurse -Force -ErrorAction SilentlyContinue

Push-Location -LiteralPath $BackendDir
try {
    & $BackendPython -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --name smart-home-demo-server `
        --paths $BackendDir `
        --distpath $PyInstallerDist `
        --workpath $PyInstallerBuild `
        --specpath $PyInstallerSpec `
        demo_server.py
} finally {
    Pop-Location
}

Write-Step "assembling package"
Remove-Item -LiteralPath $PackageDir, $ZipPath -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $PackageDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PackageDir "data") | Out-Null

Copy-Item -LiteralPath (Join-Path $PyInstallerDist "smart-home-demo-server.exe") -Destination $PackageDir
Copy-Item -LiteralPath (Join-Path $FrontendDir "dist") -Destination (Join-Path $PackageDir "frontend-dist") -Recurse

$env:SMART_HOME_DATA_DIR = Join-Path $PackageDir "data"
try {
    Push-Location -LiteralPath $BackendDir
    try {
        & $BackendPython -m app.db.seed_demo_data
    } finally {
        Pop-Location
    }
} finally {
    Remove-Item Env:\SMART_HOME_DATA_DIR -ErrorAction SilentlyContinue
}

$StartDemoBat = @(
    '@echo off',
    'cd /d "%~dp0"',
    'echo Starting Smart Home Demo...',
    'start "Smart Home Demo Server" "%~dp0smart-home-demo-server.exe"',
    'powershell -NoProfile -ExecutionPolicy Bypass -Command "$url=''http://127.0.0.1:8000/api/health''; for ($i=0; $i -lt 30; $i++) { try { Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 1 | Out-Null; Start-Process ''http://127.0.0.1:8000''; exit 0 } catch { Start-Sleep -Seconds 1 } }; Write-Host ''Server did not become ready on http://127.0.0.1:8000''; Read-Host ''Press Enter to exit''"'
)
Set-Content -LiteralPath (Join-Path $PackageDir "start-demo.bat") -Value $StartDemoBat -Encoding ASCII

$ReadmeText = @(
    'Smart Home Voice Assistant Demo Package',
    '',
    'How to start:',
    '1. Double-click start-demo.bat.',
    '2. Open http://127.0.0.1:8000 in the browser.',
    '3. Log in with the default account:',
    '   Username: testuser',
    '   Password: test123456',
    '',
    'Notes:',
    '- This demo package does not require Python or Node.js on the target machine.',
    '- Text commands, browser speech recognition, device control, scenes, reminders, logs, and personalization are available.',
    '- Xunfei cloud ASR requires AppID, APIKey, APISecret, and network access.',
    '- Local data is stored in data/app.db. Delete that file and restart to recreate default demo data.',
    '- If port 8000 is occupied, close the process that is using it first.'
)
Set-Content -LiteralPath (Join-Path $PackageDir "README-start.txt") -Value $ReadmeText -Encoding UTF8

Write-Step "creating zip"
Compress-Archive -Path (Join-Path $PackageDir "*") -DestinationPath $ZipPath -Force

Write-Step "done"
Write-Host "Package: $ZipPath"
