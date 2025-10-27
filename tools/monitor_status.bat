@echo off
REM Monitor workflow status log in real-time
REM Usage: monitor_status.bat [workflow_directory]
REM Example: monitor_status.bat Descriptions\workflow_vacation_photos
REM 
REM If no directory specified, uses wildcard to find latest workflow

setlocal enabledelayedexpansion

if "%~1"=="" (
    set "STATUS_FILE=Descriptions\workflow_*\logs\status.log"
    echo Monitoring: %STATUS_FILE%
    echo.
    echo Press Ctrl+C to stop
    echo.
) else (
    set "STATUS_FILE=%~1\logs\status.log"
    echo Checking for: %STATUS_FILE%
    echo.
    REM Don't check if file exists yet - it might be created during workflow
    echo Monitoring: %STATUS_FILE%
    echo.
    echo Press Ctrl+C to stop
    echo.
)

:loop
cls
echo ======================================
echo   Workflow Status Monitor
echo ======================================
echo.
type %STATUS_FILE% 2>nul
if errorlevel 1 (
    echo Waiting for workflow to start...
)
echo.
echo ======================================
echo Last updated: %date% %time%
echo Press Ctrl+C to stop
echo ======================================
timeout /t 2 /nobreak > nul
goto loop
