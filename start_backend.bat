@echo off
title Research Co-Pilot v2 - Backend

cd /d "%~dp0"

:: ACTIVATE VIRTUAL ENVIRONMENT
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Virtual environment not found
    echo Please run setup.bat first
    pause
    exit /b 1
)

echo [OK] Virtual environment activated
echo [INFO] Starting backend on http://localhost:8000

:: START UVICORN WITH FULL PATH
venv\Scripts\python.exe -m uvicorn backend:app --reload --port 8000 --host 0.0.0.0

pause