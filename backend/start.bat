@echo off
REM Quick start script for Property Agent UI - Windows
REM Complete end-to-end setup

echo ================================
echo Property Agent UI - Quick Start
echo ================================

REM Check Python
python --version >nul 2>&1 || (
    echo ERROR: Python not found
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo OK Python %PYTHON_VERSION%

REM Backend setup
echo.
echo Setting up backend...
cd backend

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -q -r requirements.txt

REM Check .env
if not exist ".env" (
    echo WARNING: .env not found. Copying from .env.example...
    copy .env.example .env
    echo WARNING: Please edit .env with your Chutes AI credentials
)

REM Run startup checks
echo.
echo Running startup checks...
python startup.py

pause

