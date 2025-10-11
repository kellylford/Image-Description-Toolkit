@echo off
SETLOCAL
REM Run workflow with Ollama llava:latest
REM Usage: run_ollama_llava.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Capture the original working directory before changing directories
SET ORIGINAL_CWD=%CD%

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
dist\idt.exe workflow --provider ollama --model llava:latest --output-dir ../Descriptions --original-cwd "%ORIGINAL_CWD%" %*
ENDLOCAL
