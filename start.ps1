param(
    [switch]$Reload,
    [switch]$SetupOnly,
    [switch]$NoBrowser,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$VenvDir = Join-Path $BackendDir ".venv"
$BackendPython = Join-Path $VenvDir "Scripts\python.exe"
$BackendPort = 8000
$FrontendPort = 5173

function Write-Step {
    param([string]$Message)
    Write-Host "[start] $Message"
}

function Require-Command {
    param(
        [string]$Name,
        [string]$InstallHint
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "$Name was not found. $InstallHint"
    }
    return $command.Source
}

function Get-HashText {
    param([string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

function Test-ListeningPort {
    param([int]$Port)
    $listener = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return [bool]$listener
}

function Wait-Http {
    param(
        [string]$Url,
        [int]$Attempts = 30
    )

    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    throw "Timed out waiting for $Url"
}

function Start-PowerShellWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Command
    )

    $powerShell = Require-Command "powershell.exe" "PowerShell is required on Windows."
    $escapedTitle = $Title.Replace("'", "''")
    $escapedWorkingDirectory = $WorkingDirectory.Replace("'", "''")
    $windowCommand = "Set-Location -LiteralPath '$escapedWorkingDirectory'; `$Host.UI.RawUI.WindowTitle = '$escapedTitle'; $Command"

    Start-Process -FilePath $powerShell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $windowCommand
    ) | Out-Null
}

Set-Location -LiteralPath $RootDir

Write-Step "checking local tools"
$SystemPython = Require-Command "python.exe" "Install Python 3.12+ and make sure python.exe is on PATH."
$Npm = Require-Command "npm.cmd" "Install Node.js 20+ and make sure npm.cmd is on PATH."

if (-not (Test-Path -LiteralPath $BackendDir)) {
    throw "backend directory was not found under $RootDir"
}
if (-not (Test-Path -LiteralPath $FrontendDir)) {
    throw "frontend directory was not found under $RootDir"
}

if (-not (Test-Path -LiteralPath $BackendPython)) {
    Write-Step "creating backend virtual environment"
    & $SystemPython -m venv $VenvDir
}

if (-not $SkipInstall) {
    $requirements = Join-Path $BackendDir "requirements.txt"
    $requirementsMarker = Join-Path $VenvDir ".requirements.sha256"
    $requirementsHash = Get-HashText $requirements
    $installedRequirementsHash = ""
    if (Test-Path -LiteralPath $requirementsMarker) {
        $installedRequirementsHash = Get-Content -LiteralPath $requirementsMarker -Raw
    }

    if ($requirementsHash -ne $installedRequirementsHash.Trim()) {
        Write-Step "installing backend dependencies"
        & $BackendPython -m pip install -r $requirements
        Set-Content -LiteralPath $requirementsMarker -Value $requirementsHash -NoNewline
    } else {
        Write-Step "backend dependencies are up to date"
    }

    $packageLock = Join-Path $FrontendDir "package-lock.json"
    $packageJson = Join-Path $FrontendDir "package.json"
    $frontendDependencyFile = $packageJson
    if (Test-Path -LiteralPath $packageLock) {
        $frontendDependencyFile = $packageLock
    }

    $nodeModules = Join-Path $FrontendDir "node_modules"
    $frontendMarker = Join-Path $nodeModules ".frontend-deps.sha256"
    $frontendHash = Get-HashText $frontendDependencyFile
    $installedFrontendHash = ""
    if (Test-Path -LiteralPath $frontendMarker) {
        $installedFrontendHash = Get-Content -LiteralPath $frontendMarker -Raw
    }

    if ((-not (Test-Path -LiteralPath $nodeModules)) -or $frontendHash -ne $installedFrontendHash.Trim()) {
        Write-Step "installing frontend dependencies"
        Push-Location -LiteralPath $FrontendDir
        try {
            & $Npm install
        } finally {
            Pop-Location
        }
        Set-Content -LiteralPath $frontendMarker -Value $frontendHash -NoNewline
    } else {
        Write-Step "frontend dependencies are up to date"
    }
} else {
    Write-Step "dependency installation skipped"
}

Write-Step "initializing database"
Push-Location -LiteralPath $BackendDir
try {
    & $BackendPython -m app.db.init_db
} finally {
    Pop-Location
}

if ($SetupOnly) {
    Write-Step "setup complete"
    exit 0
}

if (Test-ListeningPort $BackendPort) {
    Write-Step "backend already listening on http://127.0.0.1:$BackendPort"
    Wait-Http "http://127.0.0.1:$BackendPort/api/health" 5
} else {
    Write-Step "starting backend on http://127.0.0.1:$BackendPort"
    $backendArgs = "-m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort"
    if ($Reload) {
        $backendArgs = "$backendArgs --reload"
    }
    Start-PowerShellWindow "Smart Home Backend" $BackendDir "& '$BackendPython' $backendArgs"
    Wait-Http "http://127.0.0.1:$BackendPort/api/health" 30
}

if (Test-ListeningPort $FrontendPort) {
    Write-Step "frontend already listening on http://127.0.0.1:$FrontendPort"
    Wait-Http "http://127.0.0.1:$FrontendPort/" 10
} else {
    Write-Step "starting frontend on http://127.0.0.1:$FrontendPort"
    Start-PowerShellWindow "Smart Home Frontend" $FrontendDir "& '$Npm' run dev"
    Wait-Http "http://127.0.0.1:$FrontendPort/" 30
}

Write-Step "backend health check passed"
Write-Step "frontend is ready"
Write-Host ""
Write-Host "Open: http://127.0.0.1:$FrontendPort/"
Write-Host "API docs: http://127.0.0.1:$BackendPort/docs"
Write-Host "Default account: testuser / test123456"

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:$FrontendPort/" | Out-Null
}
