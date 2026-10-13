@echo off
setlocal enableextensions
title NINTENDER CRACK

cd /d "%~dp0"

echo.
echo  ==========================================================
echo    NINTENDER CRACK  -  one click (no admin needed)
echo  ==========================================================
echo.

if not exist "%~dp0nintender.exe" (
    echo [!] nintender.exe not found in this folder. Put it next to this .bat.
    timeout /t 8 >nul
    exit /b 1
)

:: ---- 1. find Python (per-user, no admin) ----
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY ( where py >nul 2>&1 && set "PY=py" )
if not defined PY ( for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PY=%%D\python.exe" )
if not defined PY ( for /d %%D in ("%ProgramFiles%\Python3*") do if exist "%%D\python.exe" set "PY=%%D\python.exe" )
if not defined PY (
    echo [!] Python not found - installing Python 3.12 automatically...
    winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PY=%%D\python.exe"
    if not defined PY ( for /d %%D in ("%ProgramFiles%\Python3*") do if exist "%%D\python.exe" set "PY=%%D\python.exe" )
)
if not defined PY (
    echo [!] Could not install Python automatically.
    echo     Install Python 3 from https://www.python.org/downloads/ then re-run.
    timeout /t 10 >nul
    exit /b 1
)
echo [*] Python: %PY%

:: ---- 2. install deps (no admin) ----
echo [*] Installing frida + cryptography...
"%PY%" -m pip install --quiet --no-input --disable-pip-version-check frida cryptography 2>nul
if errorlevel 1 "%PY%" -m pip install --quiet --no-input --user frida cryptography

:: ---- 3. launch ----
echo [*] Launching...
echo.
"%PY%" "%~dp0crack_final.py"
if errorlevel 1 ( timeout /t 10 >nul )
exit /b
