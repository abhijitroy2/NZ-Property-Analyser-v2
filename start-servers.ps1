# Start backend and frontend servers in separate windows
# Run from project root: .\start-servers.ps1

$projectRoot = $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"
$frontendPath = Join-Path $projectRoot "frontend"

Write-Host "Starting NZ Property Finder servers..." -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Gray
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Gray
Write-Host ""

# Resolve Python: prefer venv, else py launcher
$venvPython = Join-Path $backendPath "venv\Scripts\python.exe"
$backendCmd = if (Test-Path $venvPython) {
    "cd '$backendPath'; Write-Host 'Backend (FastAPI) - http://localhost:8000' -ForegroundColor Green; & '$venvPython' -m uvicorn app.main:app --reload --port 8000"
} else {
    "cd '$backendPath'; Write-Host 'Backend (FastAPI) - http://localhost:8000' -ForegroundColor Green; py -m uvicorn app.main:app --reload --port 8000"
}

# Start backend in new window
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $backendCmd)

# Brief pause so windows open in order
Start-Sleep -Seconds 1

# Start frontend in new window
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendPath'; Write-Host 'Frontend (Next.js) - http://localhost:3000' -ForegroundColor Green; npm run dev"
)

Write-Host "Two terminal windows opened. Close each window to stop its server." -ForegroundColor Yellow
