@echo off
REM Run workflow with Ollama InternVL (strong vision-language model)
REM Usage: run_ollama_internvl.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model internvl:latest --prompt-style narrative --output-dir ..\Descriptions %1
