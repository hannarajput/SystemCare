@echo off
setlocal
title SystemCare — PC Health ^& Performance Optimizer
cd /d "%~dp0"

echo [SystemCare] Checking runtime environment...

:: Verify Python installation
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in system PATH.
    echo Please install Python 3.10 or newer from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Verify dependencies
python -c "import customtkinter, psutil, PIL" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Required Python packages appear to be missing.
    echo Installing dependencies from requirements.txt...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install dependencies. Please run 'pip install -r requirements.txt' manually.
        pause
        exit /b 1
    )
)

echo [SystemCare] Launching application...
python main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [SystemCare] The application closed with an exit code of %ERRORLEVEL%.
    pause
)
endlocal
