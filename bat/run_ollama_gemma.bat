@echo off
REM Run workflow with Ollama Gemma 3 (Google's vision model)
REM Usage: run_ollama_gemma.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model gemma3:latest --prompt-style narrative --output-dir ..\Descriptions %1
