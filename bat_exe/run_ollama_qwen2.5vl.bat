@echo off
SETLOCAL
REM Run workflow with Ollama Qwen2.5-VL
REM Usage: run_ollama_qwen2.5vl.bat [options] <image_directory>
REM Supports all workflow options in any order

..\idt.exe workflow --provider ollama --model qwen2.5vl --output-dir ..\Descriptions %*
ENDLOCAL
