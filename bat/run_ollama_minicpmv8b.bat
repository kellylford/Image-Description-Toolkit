@echo off
REM Run workflow with Ollama MiniCPM-V 8B (larger Chinese vision model)
REM Usage: run_ollama_minicpmv8b.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model minicpm-v:8b --prompt-style narrative --output-dir ..\Descriptions %1
