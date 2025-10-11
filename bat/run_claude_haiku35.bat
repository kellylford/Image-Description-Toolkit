@echo off
SETLOCAL
REM Run workflow with Ollama claude-3-5-haiku-20241022
REM Usage: run_claude_haiku35.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
python workflow.py --provider ollama --model claude-3-5-haiku-20241022 --output-dir Descriptions %*
ENDLOCAL
