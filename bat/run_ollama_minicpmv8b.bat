@echo off
SETLOCAL
REM Run workflow with Ollama minicpm-v:8b
REM Usage: run_ollama_minicpmv8b.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
python workflow.py --provider ollama --model minicpm-v:8b --output-dir Descriptions %*
ENDLOCAL
