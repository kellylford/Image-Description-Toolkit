@echo off
REM Quick batch file to run Llama 3.2 Vision model via Ollama on September 2025 photos

python workflow.py "\\ford\home\Photos\MobileBackup\iPhone\2025\09" ^
  --provider ollama ^
  --model llama3.2-vision ^
  --prompt-style narrative ^
  --steps video,convert,describe,html

echo.
echo Llama 3.2 Vision workflow complete!
pause
