@echo off
SETLOCAL
REM Run workflow with Ollama claude-opus-4-1-20250805
REM Usage: run_claude_opus41.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
python workflow.py --provider ollama --model claude-opus-4-1-20250805 --output-dir Descriptions %*
ENDLOCAL
