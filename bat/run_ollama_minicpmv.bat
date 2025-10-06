@echo off
REM Run workflow with Ollama MiniCPM-V (efficient Chinese vision model)
REM Usage: run_ollama_minicpmv.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model minicpm-v:latest --prompt-style narrative --output-dir ..\Descriptions %1
