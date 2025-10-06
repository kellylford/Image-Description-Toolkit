@echo off
REM Run workflow with Ollama LLaVA 34B (highest quality LLaVA)
REM Usage: run_ollama_llava34b.bat <image_directory>

..\.venv\Scripts\python.exe ..\workflow.py --provider ollama --model llava:34b --prompt-style narrative --output-dir ..\Descriptions %1
