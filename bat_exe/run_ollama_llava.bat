@echo off
SETLOCAL
REM Run workflow with Ollama LLaVA (latest)
REM Usage: run_ollama_llava.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_ollama_llava.bat --prompt-style colorful test_images
REM   run_ollama_llava.bat test_images --dry-run

..\idt.exe workflow --provider ollama --model llava:latest --output-dir ..\Descriptions %*
ENDLOCAL
