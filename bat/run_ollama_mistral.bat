@echo off
REM Run workflow with Ollama Mistral Small 3.1
REM Usage: run_ollama_mistral.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model mistral-small3.1:latest --prompt-style narrative --output-dir ..\Descriptions %1
