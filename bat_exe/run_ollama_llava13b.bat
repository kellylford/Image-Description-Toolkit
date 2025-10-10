@echo off
SETLOCAL
REM Run workflow with Ollama llava:13b
REM Usage: run_ollama_llava13b.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0.."
idt.exe workflow --provider ollama --model llava:13b --output-dir Descriptions %*
ENDLOCAL
