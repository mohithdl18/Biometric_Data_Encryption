@echo off
echo ========================================
echo Face Registration Backend Setup
echo ========================================

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "..\.venv" (
    echo Error: Virtual environment not found!
    echo Please create it first:
    echo 1. cd to project root directory
    echo 2. python -m venv .venv
    echo 3. .venv\Scripts\activate
    pause
    exit /b 1
)

echo Installing required packages...
"..\.venv\Scripts\pip.exe" install -r requirements.txt

if %errorlevel% neq 0 (
    echo Failed to install packages!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Starting Flask Backend Server
echo ========================================
echo Server will be available at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

"..\.venv\Scripts\python.exe" app.py

pause
