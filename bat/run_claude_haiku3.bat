@echo off
SETLOCAL
REM Run workflow with Ollama claude-3-haiku-20240307
REM Usage: run_claude_haiku3.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
python workflow.py --provider ollama --model claude-3-haiku-20240307 --output-dir Descriptions %*
ENDLOCAL
