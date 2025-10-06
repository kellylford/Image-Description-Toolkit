@echo off
REM Run workflow with Ollama LLaVA-Phi3 (small but mighty, 2.9GB)
REM Usage: run_ollama_llava_phi3.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model llava-phi3:latest --prompt-style narrative --output-dir ..\Descriptions %1
