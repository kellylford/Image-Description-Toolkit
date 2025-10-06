@echo off
REM Run workflow with Ollama CogVLM2 (advanced Chinese vision-language model)
REM Usage: run_ollama_cogvlm2.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model cogvlm2:latest --prompt-style narrative --output-dir ..\Descriptions %1
