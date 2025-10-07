@echo off
REM Run workflow with Ollama qwen2.5vl
REM Usage: run_ollama_qwen2.5vl.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model qwen2.5vl --prompt-style narrative --output-dir ..\Descriptions %1
