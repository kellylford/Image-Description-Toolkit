@echo off
echo Image Gallery Alt Text Generation
echo ================================
echo.
echo This script will add Claude Haiku-generated alt text to your JSON files.
echo.

REM Check if API key is set
if "%ANTHROPIC_API_KEY%"=="" (
    echo Error: ANTHROPIC_API_KEY environment variable is not set.
    echo.
    echo To set your Claude API key, run one of these commands:
    echo   For current session: set ANTHROPIC_API_KEY=your_key_here
    echo   For permanent:       setx ANTHROPIC_API_KEY "your_key_here"
    echo.
    echo Then run this script again.
    pause
    exit /b 1
)

echo API key found. Generating alt text...
echo.

python generate_alt_text.py

if %ERRORLEVEL%==0 (
    echo.
    echo Alt text generation completed successfully!
    echo Your JSON files now contain accessible alt text for the website.
) else (
    echo.
    echo Alt text generation failed. Check the error messages above.
)

echo.
pause