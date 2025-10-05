@echo off
cd /d "%~dp0..\.." && python workflow.py "\\ford\home\photos\MobileBackup\iPhone\2025\09" --provider openai --model gpt-4o-mini --prompt-style narrative --api-key-file "C:\Users\kelly\GitHub\idt\BatForScripts\myversion\openai.txt" --steps video,convert,describe,html
pause
