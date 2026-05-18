@echo off
title Scholar Graphite v2 - Backend + Frontend
echo.
echo ============================================
echo   Academic Research Co-Pilot v2
echo   Starting Backend (FastAPI) and Frontend (React)
echo ============================================
echo.

:: Check if we're in the correct directory
if not exist "backend.py" (
    echo [ERROR] backend.py not found. Please run this script from the project root.
    pause
    exit /b 1
)

:: Check virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Please run setup first:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

:: Check frontend dependencies
if not exist "frontend\package.json" (
    echo [ERROR] Frontend package.json not found.
    pause
    exit /b 1
)

:: Start backend in background
echo [INFO] Starting backend on port 8000...
start "Backend" /min cmd /c "call venv\Scripts\activate.bat && uvicorn backend:app --reload --port 8000 --host 0.0.0.0"

:: Wait a moment for backend to start
timeout /t 3 /nobreak > nul

:: Start frontend in background
echo [INFO] Starting frontend on port 3000...
start "Frontend" /min cmd /c "cd frontend && npm run dev"

echo.
echo ============================================
echo   Services Started!
echo   Backend: http://localhost:8000/api/health
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Press any key to stop both services...
pause > nul

:: Kill the running services
echo [INFO] Stopping services...
taskkill /FI "WINDOWTITLE eq Backend*" /F > nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend*" /F > nul 2>&1
echo [OK] Services stopped.

:: Check if backend is running
curl http://localhost:8000/api/health > nul 2>&1
if %errorlevel% equ 0 (
    echo [WARNING] Backend may still be running. Use Ctrl+C in its terminal to stop.
) else (
    echo [OK] Both services stopped successfully.
)