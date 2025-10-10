@echo off
SETLOCAL
REM Run workflow with Ollama BakLLaVA (BakLLaVA variant)
REM Usage: run_ollama_bakllava.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_ollama_bakllava.bat --prompt-style colorful test_images
REM   run_ollama_bakllava.bat test_images --dry-run

..\idt.exe workflow --provider ollama --model bakllava:latest --output-dir ..\Descriptions %*
ENDLOCAL
