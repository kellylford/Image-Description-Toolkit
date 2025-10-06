@echo off
REM Run workflow with Ollama BakLLaVA (vision model variant)
REM Usage: run_ollama_bakllava.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model bakllava:latest --prompt-style narrative --output-dir ..\Descriptions %1
