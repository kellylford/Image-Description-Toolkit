@echo off
REM Run workflow with Ollama Llama 3.2 Vision (latest)
REM Usage: run_ollama_llama32vision.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model llama3.2-vision:latest --prompt-style narrative --output-dir ..\Descriptions %1
