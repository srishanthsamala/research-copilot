@echo off
title Research Co-Pilot — Frontend (React)
echo.
echo  ============================================
echo   Academic Research Co-Pilot — Frontend
echo   React + Vite on http://localhost:3000
echo  ============================================
echo.

cd /d "%~dp0\frontend"

:: Check node_modules
if not exist "node_modules" (
    echo [..] Installing npm packages ^(first time only^)...
    npm install
    echo.
)

echo [OK] Dependencies ready
echo [..] Starting React frontend on http://localhost:3000
echo.
echo  Open your browser at: http://localhost:3000
echo  Press Ctrl+C to stop
echo.

npm run dev

pause
