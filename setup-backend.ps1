# One-time backend setup: create venv and install dependencies
# Run from project root: .\setup-backend.ps1

$backendPath = Join-Path $PSScriptRoot "backend"
$venvPath = Join-Path $backendPath "venv"

Write-Host "Setting up backend..." -ForegroundColor Cyan
Set-Location $backendPath

# Find Python - try PATH first, then common install locations
$pyExe = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $pyExe = "py" }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $pyExe = "python" }
else {
    $localPython = "$env:LOCALAPPDATA\Python"
    $candidates = @(
        "$localPython\pythoncore-3.14-64\python.exe",
        "$localPython\bin\python.exe"
    )
    $candidates += Get-ChildItem -Path $localPython -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p)) { $pyExe = $p; break }
    }
}
if (-not $pyExe) {
    Write-Host "ERROR: Python not found." -ForegroundColor Red
    Write-Host "PATH has Scripts - you need the parent folder. Add to PATH:" -ForegroundColor Yellow
    Write-Host "  $env:LOCALAPPDATA\Python\pythoncore-3.14-64" -ForegroundColor Gray
    exit 1
}

Write-Host "Using Python: $pyExe" -ForegroundColor Gray

# Create venv if missing
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $pyExe -m venv venv
    if ($LASTEXITCODE -ne 0) { exit 1 }
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Gray
}

# Install dependencies
$venvPython = Join-Path $venvPath "Scripts\python.exe"
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit 1 }

# Create .env from example if missing
$envExample = Join-Path $backendPath ".env.example"
$envFile = Join-Path $backendPath ".env"
if ((Test-Path $envExample) -and -not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "Created .env from .env.example - edit with your settings." -ForegroundColor Yellow
}

Write-Host "Backend setup complete!" -ForegroundColor Green
Write-Host "Run .\start-servers.ps1 to start the app." -ForegroundColor Gray
