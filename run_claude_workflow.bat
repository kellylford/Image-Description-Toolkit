@echo off
REM Run Claude workflow for iPhone photos September 2025

echo ============================================================
echo Running Claude Workflow
echo ============================================================
echo.
echo Input directory: \\ford\home\photos\MobileBackup\iPhone\2025\09
echo Provider: Claude
echo Model: claude-sonnet-4-5-20250929
echo Prompt Style: narrative
echo API Key: BatForScripts\myversion\claude.txt
echo.
pause

cd /d "%~dp0"

.venv\Scripts\python.exe workflow.py "\\ford\home\photos\MobileBackup\iPhone\2025\09" --provider claude --model claude-sonnet-4-5-20250929 --prompt-style narrative --api-key-file "c:\users\kelly\onedrive\claude.txt"

echo.
echo ============================================================
echo Workflow Complete!
echo ============================================================
echo.
pause
