@echo off
REM ============================================================================
REM Create Distribution Package for Image Description Toolkit
REM ============================================================================
REM This script creates a distributable ZIP file with the executable and
REM all necessary files for end users.
REM
REM Prerequisites:
REM   - Built executable in dist/ folder (run build.bat first)
REM
REM Output:
REM   - releases/ImageDescriptionToolkit_v[VERSION].zip
REM
REM IMPORTANT: This script does NOT modify your repository files!
REM   - Batch files in your repo stay as "python workflow.py"
REM   - Only the STAGING copy gets converted to use the .exe
REM   - Your git repository remains unchanged
REM ============================================================================

echo.
echo ========================================================================
echo Creating Distribution Package
echo ========================================================================
echo.

REM Check if executable exists
if not exist "dist\idt.exe" (
    echo ERROR: Executable not found!
    echo.
    echo Please run build.bat first to create the executable.
    echo.
    pause
    exit /b 1
)

REM Get version
set VERSION=unknown
if exist "VERSION" (
    set /p VERSION=<VERSION
)

REM Create releases directory
if not exist "releases" mkdir releases

REM Create temporary staging directory
set STAGE_DIR=releases\staging
if exist "%STAGE_DIR%" rmdir /s /q "%STAGE_DIR%"
mkdir "%STAGE_DIR%"

echo [1/5] Copying executable...
copy "dist\idt.exe" "%STAGE_DIR%\" >nul
echo     Done.
echo.

echo [2/5] Copying and converting batch files for executable use...
mkdir "%STAGE_DIR%\bat"
xcopy "bat_exe\*.bat" "%STAGE_DIR%\bat\" /Y /Q >nul

REM Convert batch files from dist\idt.exe to idt.exe in staging
echo     Converting batch files (dist\idt.exe → idt.exe)...
for %%f in ("%STAGE_DIR%\bat\*.bat") do (
    powershell -command "(Get-Content '%%f' -Raw) -replace 'dist\\idt\.exe', 'idt.exe' | Set-Content '%%f' -NoNewline -Encoding ASCII"
)
echo     Done.
echo.

echo [3/5] Creating directory structure...
mkdir "%STAGE_DIR%\Descriptions"
mkdir "%STAGE_DIR%\analysis"
mkdir "%STAGE_DIR%\analysis\results"
mkdir "%STAGE_DIR%\scripts"

REM Copy essential JSON configs that users might want to customize
copy "scripts\workflow_config.json" "%STAGE_DIR%\scripts\" >nul
copy "scripts\image_describer_config.json" "%STAGE_DIR%\scripts\" >nul
copy "scripts\video_frame_extractor_config.json" "%STAGE_DIR%\scripts\" >nul

echo     Done.
echo.

echo [4/5] Copying documentation...
mkdir "%STAGE_DIR%\docs"
xcopy "docs\*.md" "%STAGE_DIR%\docs\" /Y /Q >nul
copy "README.md" "%STAGE_DIR%\" >nul
copy "QUICK_START.md" "%STAGE_DIR%\" >nul
copy "LICENSE" "%STAGE_DIR%\" >nul
copy "VERSION" "%STAGE_DIR%\" >nul

REM Create simplified README for exe distribution
echo Creating Image Description Toolkit distribution package... > "%STAGE_DIR%\README.txt"
echo. >> "%STAGE_DIR%\README.txt"
echo Image Description Toolkit v%VERSION% >> "%STAGE_DIR%\README.txt"
echo Executable Distribution >> "%STAGE_DIR%\README.txt"
echo. >> "%STAGE_DIR%\README.txt"
echo For complete documentation, see docs\USER_GUIDE.md >> "%STAGE_DIR%\README.txt"
echo. >> "%STAGE_DIR%\README.txt"
echo QUICK START: >> "%STAGE_DIR%\README.txt"
echo   1. Download and install Ollama from https://ollama.com >> "%STAGE_DIR%\README.txt"
echo   2. Pull at least one Ollama model (e.g., ollama pull llava) >> "%STAGE_DIR%\README.txt"
echo   3. From the root of where you unpacked: idt guideme >> "%STAGE_DIR%\README.txt"
echo   4. See bat files for more examples >> "%STAGE_DIR%\README.txt"
echo. >> "%STAGE_DIR%\README.txt"
echo For detailed usage instructions, see docs\USER_GUIDE.md >> "%STAGE_DIR%\README.txt"

echo     Done.
echo.

echo [5/5] Creating ZIP archive...
set ZIP_NAME=ImageDescriptionToolkit_v%VERSION%.zip
if exist "releases\%ZIP_NAME%" del "releases\%ZIP_NAME%"

REM Use PowerShell to create ZIP (built into Windows)
powershell -command "Compress-Archive -Path '%STAGE_DIR%\*' -DestinationPath 'releases\%ZIP_NAME%' -CompressionLevel Optimal"

if errorlevel 1 (
    echo ERROR: Failed to create ZIP file
    echo.
    pause
    exit /b 1
)

REM Get ZIP size
for %%A in ("releases\%ZIP_NAME%") do set size=%%~zA
set /a size_mb=%size% / 1048576

echo     Done.
echo.

REM Cleanup staging directory
rmdir /s /q "%STAGE_DIR%"

echo ========================================================================
echo Distribution Package Created!
echo ========================================================================
echo.
echo Package: releases\%ZIP_NAME%
echo Size: %size_mb% MB (compressed)
echo.
echo This package includes:
echo   - idt.exe (single executable)
echo   - All batch files (ready to use)
echo   - install_ollama.bat (automatic Ollama installer)
echo   - Directory structure (Descriptions, analysis, etc.)
echo   - Documentation (README, QUICK_START, docs)
echo   - Sample configurations
echo.
echo Users can:
echo   1. Extract ZIP to any folder
echo   2. Run bat\install_ollama.bat (or install Ollama manually)
echo   3. Run batch files immediately - no Python needed!
echo.
echo Ready for distribution!
echo.
pause
