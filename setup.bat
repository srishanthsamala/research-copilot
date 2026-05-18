@echo off
title Research Co-Pilot v2 - Setup

cd /d "%~dp0"

:: Create/update virtual environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

:: ACTIVATE VIRTUAL ENVIRONMENT
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

:: Install Python dependencies
pip install -r requirements.txt

:: Ensure uvicorn is installed in venv
python -m pip install uvicorn --target=venv\Lib

:: Verify installation
echo.
echo Uvicorn version: $(python -c "import uvicorn; print(uvicorn.__version__)")
echo.
echo Setup complete! Run start_backend.bat to start services

