@echo off
REM Quick batch file to run Moondream model via Ollama on September 2025 photos

python workflow.py "\\ford\home\Photos\MobileBackup\iPhone\2025\09" ^
  --provider ollama ^
  --model moondream ^
  --prompt-style narrative ^
  --steps video,convert,describe,html

echo.
echo Moondream workflow complete!
pause
