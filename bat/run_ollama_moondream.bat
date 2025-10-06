@echo off
REM Run workflow with Ollama Moondream (fastest, smallest)
REM Usage: run_ollama_moondream.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model moondream:latest --prompt-style narrative --output-dir ..\Descriptions %1
