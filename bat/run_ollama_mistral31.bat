@echo off
SETLOCAL
REM Run workflow with Ollama mistral-small3.1:latest
REM Usage: run_ollama_mistral31.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
python workflow.py --provider ollama --model mistral-small3.1:latest --output-dir Descriptions %*
ENDLOCAL
