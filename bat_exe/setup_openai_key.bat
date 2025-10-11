@echo off
REM Setup OpenAI API key as environment variable
REM Usage: setup_openai_key.bat <openai_api_key.txt>
REM
REM This sets OPENAI_API_KEY for the current session only.
REM To make it permanent, add it to your System Environment Variables.

if "%1"=="" (
    echo Usage: setup_openai_key.bat ^<path_to_api_key_file^>
    echo Example: setup_openai_key.bat C:\Keys\openai.txt
    exit /b 1
)
if not exist "%1" (
    echo Error: File "%1" not found
    exit /b 1
)
for /f "delims=" %%i in ('type "%1"') do set OPENAI_API_KEY=%%i
echo OPENAI_API_KEY environment variable set for this session.
echo To verify: echo %OPENAI_API_KEY%
