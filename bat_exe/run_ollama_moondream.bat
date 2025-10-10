@echo off
SETLOCAL
REM Run workflow with Ollama Moondream (fastest, smallest)
REM Usage: run_ollama_moondream.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_ollama_moondream.bat --prompt-style colorful test_images
REM   run_ollama_moondream.bat test_images --dry-run

..\idt.exe workflow --provider ollama --model moondream:latest --output-dir ..\Descriptions %*
ENDLOCAL
