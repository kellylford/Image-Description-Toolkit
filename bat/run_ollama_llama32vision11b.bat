@echo off
REM Run workflow with Ollama Llama 3.2 Vision 11B (most accurate)
REM Usage: run_ollama_llama32vision11b.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model llama3.2-vision:11b --prompt-style narrative --output-dir ..\Descriptions %1
