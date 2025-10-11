@echo off
SETLOCAL
REM Run workflow with Ollama llava:7b
REM Usage: run_ollama_llava7b.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
python workflow.py --provider ollama --model llava:7b --output-dir Descriptions %*
ENDLOCAL
