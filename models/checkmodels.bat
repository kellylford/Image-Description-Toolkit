@echo off
REM ================================================================
REM    ImageDescriber - Model Status Checker
REM ================================================================
REM
REM This script checks the status of all AI models and providers
REM across the Image Description Toolkit.
REM
REM Usage:
REM   checkmodels.bat                    - Check all providers
REM   checkmodels.bat ollama             - Check specific provider
REM   checkmodels.bat --verbose          - Show detailed info
REM   checkmodels.bat --json             - Output as JSON
REM

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please ensure Python is installed and in PATH.
    pause
    exit /b 1
)

REM Run the check_models.py script with all arguments
python -m models.check_models %*

REM Pause only if no arguments were passed (interactive mode)
if "%1"=="" pause
