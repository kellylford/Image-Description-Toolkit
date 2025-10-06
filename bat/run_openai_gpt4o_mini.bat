@echo off
REM Run workflow with OpenAI GPT-4o-mini (fast & affordable cloud)
REM Usage: run_openai_gpt4o_mini.bat <image_directory>
REM Requires: openai.txt with API key in current directory OR OPENAI_API_KEY environment variable

..\.venv\Scripts\python.exe ..\workflow.py --provider openai --model gpt-4o-mini --prompt-style narrative --output-dir ..\Descriptions %1
