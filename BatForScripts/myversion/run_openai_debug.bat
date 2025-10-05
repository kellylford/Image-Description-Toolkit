@echo off

REM Path to your images
set IMAGE_PATH=\\ford\home\photos\MobileBackup\iPhone\2025\09

REM Path to file containing your OpenAI API key
set API_KEY_FILE=c:\users\kelly\onedrive\openai.txt

echo ============================================================================
echo DEBUG: Testing file existence checks
echo ============================================================================
echo.

echo IMAGE_PATH is set to: %IMAGE_PATH%
echo Checking if IMAGE_PATH exists...
if not exist "%IMAGE_PATH%" (
    echo FAIL: Image path does not exist
) else (
    echo PASS: Image path exists
)
echo.

echo API_KEY_FILE is set to: %API_KEY_FILE%
echo Checking if API_KEY_FILE exists...
if not exist "%API_KEY_FILE%" (
    echo FAIL: API key file does not exist
) else (
    echo PASS: API key file exists
)
echo.

echo Done with checks
pause
