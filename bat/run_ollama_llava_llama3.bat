@echo off
REM Run workflow with Ollama LLaVA-Llama3 (LLaVA with Llama 3 base)
REM Usage: run_ollama_llava_llama3.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model llava-llama3:latest --prompt-style narrative --output-dir ..\Descriptions %1
