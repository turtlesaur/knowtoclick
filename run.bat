@echo off
echo ========================================
echo  KnowToClick - Activity Signaler
echo ========================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Install Python 3.9+ from https://www.python.org
    echo Make sure "Add Python to PATH" is checked during install.
    pause
    exit /b 1
)

:: Install dependencies if needed
pip show pywin32 >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
    echo.
)

echo Starting KnowToClick...
echo.
python main.py
pause
