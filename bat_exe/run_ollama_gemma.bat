@echo off
SETLOCAL

REM Capture the original working directory before changing directories
SET ORIGINAL_CWD=%CD%
REM Run workflow with Ollama gemma3:latest
REM Usage: run_ollama_gemma.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
dist\idt.exe workflow --provider ollama --model gemma3:latest --output-dir ../Descriptions --original-cwd "%ORIGINAL_CWD%" %*
ENDLOCAL
