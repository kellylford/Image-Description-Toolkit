@echo off
REM Run workflow with Ollama LLaVA 13B (higher quality)
REM Usage: run_ollama_llava13b.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model llava:13b --prompt-style narrative --output-dir ..\Descriptions %1
