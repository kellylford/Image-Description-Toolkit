@echo off
REM Run workflow with Ollama LLaVA (latest)
REM Usage: run_ollama_llava.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model llava:latest --prompt-style narrative --output-dir ..\Descriptions %1
