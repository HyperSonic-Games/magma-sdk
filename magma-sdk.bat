@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo ======================================
echo Magma SDK (Windows)
echo ======================================

REM =========================
REM [1/4] Python detection
REM =========================

echo [1/4] Checking Python...

set "PYTHON="

where python >nul 2>nul
if %errorlevel%==0 set "PYTHON=python"

if not defined PYTHON (
    where py >nul 2>nul
    if %errorlevel%==0 set "PYTHON=py"
)

if not defined PYTHON (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

echo Using: %PYTHON%


REM =========================
REM [2/4] venv
REM =========================
set "VENV_DIR=.venv"

echo [2/4] Setting up venv...

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    %PYTHON% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: venv creation failed
        pause
        exit /b 1
    )
)

call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: venv activation failed
    pause
    exit /b 1
)

set "PYTHON=%VENV_DIR%\Scripts\python.exe"

REM =========================
REM [3/4] dependencies (only if file exists AND venv empty marker)
REM =========================
echo [3/4] Checking dependencies...

set "REQ_FILE=requirements.txt"
set "REQ_MARKER=%VENV_DIR%\requirements.installed"

if exist "%REQ_FILE%" goto :CHECK_MARKER
goto :RUN_STEP4

:CHECK_MARKER
if exist "%REQ_MARKER%" goto :SKIP_INSTALL

echo Installing dependencies (first run only)...
%PYTHON% -m pip install -r "%REQ_FILE%"
if errorlevel 1 (
    echo ERROR: dependency install failed
    pause
    exit /b 1
)

echo done>"%REQ_MARKER%"

:SKIP_INSTALL
echo Dependencies already installed

:RUN_STEP4

REM =========================
REM [4/4] run
REM =========================
echo [4/4] Running SDK...
echo --------------------------------------

%PYTHON% main.py %*

endlocal