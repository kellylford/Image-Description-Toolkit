@echo off
SETLOCAL
REM Run workflow with Ollama gpt-4o-mini
REM Usage: run_openai_gpt4o_mini.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
python workflow.py --provider ollama --model gpt-4o-mini --output-dir Descriptions %*
ENDLOCAL
