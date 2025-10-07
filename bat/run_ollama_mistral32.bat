@echo off
REM Run workflow with Ollama Mistral Small 3.2
REM Usage: run_ollama_mistral32.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model mistral-small3.2 --prompt-style narrative --output-dir ..\Descriptions %1
