@echo off
REM Run workflow with OpenAI GPT-5 (next generation)
REM Usage: run_openai_gpt5.bat <image_directory>
REM Requires: openai.txt with API key in current directory OR OPENAI_API_KEY environment variable

..\.venv\Scripts\python.exe ..\workflow.py --provider openai --model gpt-5 --prompt-style narrative --output-dir ..\Descriptions %1
