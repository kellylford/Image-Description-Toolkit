@echo off
SETLOCAL
REM Run workflow with Ollama minicpm-v:latest
REM Usage: run_ollama_minicpmv.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0.."
idt.exe workflow --provider ollama --model minicpm-v:latest --output-dir Descriptions %*
ENDLOCAL
