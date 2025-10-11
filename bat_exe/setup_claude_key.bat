@echo off
REM Setup Claude (Anthropic) API key as environment variable
REM Usage: setup_claude_key.bat <claude_api_key.txt>
REM
REM This sets ANTHROPIC_API_KEY for the current session only.
REM To make it permanent, add it to your System Environment Variables.

if "%1"=="" (
    echo Usage: setup_claude_key.bat ^<path_to_api_key_file^>
    echo Example: setup_claude_key.bat C:\Keys\claude.txt
    pause
    exit /b 1
)

if not exist "%1" (
    echo Error: File "%1" not found
    pause
    exit /b 1
)

for /f "delims=" %%i in ('type "%1"') do set ANTHROPIC_API_KEY=%%i
echo.
echo ✓ SUCCESS: ANTHROPIC_API_KEY environment variable set for this session.
echo.
echo To verify the key was set: echo %ANTHROPIC_API_KEY%
echo.
echo Note: This setting is only for the current command prompt session.
echo To make it permanent, add it to your System Environment Variables.
echo.
pause
