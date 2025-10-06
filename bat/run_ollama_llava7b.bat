@echo off
REM Run workflow with Ollama LLaVA 7B (balanced quality & speed)
REM Usage: run_ollama_llava7b.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model llava:7b --prompt-style narrative --output-dir ..\Descriptions %1
