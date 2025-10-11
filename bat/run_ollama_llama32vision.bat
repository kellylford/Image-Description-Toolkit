@echo off
SETLOCAL
REM Run workflow with Ollama llama3.2-vision:latest
REM Usage: run_ollama_llama32vision.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
python workflow.py --provider ollama --model llama3.2-vision:latest --output-dir Descriptions %*
ENDLOCAL
