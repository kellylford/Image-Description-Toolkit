@echo off
REM Run workflow with Ollama Llama 3.2 Vision 90B (maximum accuracy - VERY LARGE)
REM Usage: run_ollama_llama32vision90b.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model llama3.2-vision:90b --prompt-style narrative --output-dir ..\Descriptions %1
