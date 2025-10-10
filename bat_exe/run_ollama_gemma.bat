@echo off
SETLOCAL
REM Run workflow with Ollama Gemma 3 (Google's model)
REM Usage: run_ollama_gemma.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_ollama_gemma.bat --prompt-style colorful test_images
REM   run_ollama_gemma.bat test_images --dry-run

..\idt.exe workflow --provider ollama --model gemma3:latest --output-dir ..\Descriptions %*
ENDLOCAL
