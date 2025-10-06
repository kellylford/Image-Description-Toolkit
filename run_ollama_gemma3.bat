@echo off
REM Quick batch file to run Gemma 3 vision model via Ollama on September 2025 photos

python workflow.py "\\ford\home\Photos\MobileBackup\iPhone\2025\09" --provider ollama --model gemma3 --prompt-style narrative --steps video,convert,describe,html

echo.
echo Gemma 3 workflow complete!
pause
