@echo off
REM One-time backend setup: create venv and install dependencies
REM Run from project root: setup-backend.bat

echo Setting up backend...

cd /d %~dp0backend

REM Find Python - try PATH first, then common install locations
where py >nul 2>&1
if %errorlevel% equ 0 (
    set PY=py
    goto :found
)
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PY=python
    goto :found
)

REM Fallback: check AppData\Local\Python (where pythoncore typically installs)
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PY=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    goto :found
)
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY=%LOCALAPPDATA%\Python\bin\python.exe"
    goto :found
)

REM Try any pythoncore-3.x directory
for /d %%D in ("%LOCALAPPDATA%\Python\pythoncore-*") do (
    if exist "%%D\python.exe" (
        set "PY=%%D\python.exe"
        goto :found
    )
)

echo ERROR: Python not found.
echo PATH has Scripts folder - you need the parent folder too.
echo Add this to PATH: %LOCALAPPDATA%\Python\pythoncore-3.14-64
echo.
pause
exit /b 1

:found

if not exist "venv" (
    echo Creating virtual environment...
    "%PY%" -m venv venv
    if errorlevel 1 exit /b 1
) else (
    echo Virtual environment already exists.
)

echo Installing dependencies...
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

if exist .env.example if not exist .env (
    copy .env.example .env
    echo Created .env - edit with your settings.
)

echo.
echo Backend setup complete! Run start-servers.bat to start.
pause
