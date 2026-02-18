@echo off
REM Start backend and frontend servers in separate windows
REM Run from project root: start-servers.bat

echo Starting NZ Property Finder servers...
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo.

if exist "%~dp0backend\venv\Scripts\python.exe" (
    start "NZ Property Finder - Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
) else (
    start "NZ Property Finder - Backend" cmd /k "cd /d %~dp0backend && py -m uvicorn app.main:app --reload --port 8000"
)

timeout /t 2 /nobreak >nul

start "NZ Property Finder - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Two terminal windows opened. Close each window to stop its server.
pause
