@echo off
SETLOCAL
REM Run workflow with Ollama gpt-5
REM Usage: run_openai_gpt5.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
python workflow.py --provider ollama --model gpt-5 --output-dir Descriptions %*
ENDLOCAL
