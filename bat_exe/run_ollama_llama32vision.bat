@echo off
SETLOCAL
REM Run workflow with Ollama Llama 3.2 Vision (latest)
REM Usage: run_ollama_llama32vision.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_ollama_llama32vision.bat --prompt-style colorful test_images
REM   run_ollama_llama32vision.bat test_images --dry-run

..\idt.exe workflow --provider ollama --model llama3.2-vision:latest --output-dir ..\Descriptions %*
ENDLOCAL
