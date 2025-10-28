@echo off
REM ============================================================================
REM Automated Build-Test-Deploy-Validate Pipeline
REM ============================================================================
REM This script provides a complete automation pipeline:
REM   1. Run unit tests on code changes
REM   2. Build executable with PyInstaller
REM   3. Deploy to installation directory
REM   4. Run validation workflow on frozen executable
REM   5. Verify results
REM
REM Usage:
REM   build-test-deploy.bat [install_dir] [test_images_dir]
REM
REM Examples:
REM   build-test-deploy.bat c:\idt2 c:\idt2\testimages
REM   build-test-deploy.bat
REM ============================================================================

setlocal enabledelayedexpansion

REM Default directories
set INSTALL_DIR=c:\idt2
set TEST_IMAGES_DIR=c:\idt2\testimages

REM Override with command line args if provided
if not "%~1"=="" set INSTALL_DIR=%~1
if not "%~2"=="" set TEST_IMAGES_DIR=%~2

echo.
echo ============================================================================
echo IDT Automated Build-Test-Deploy-Validate Pipeline
echo ============================================================================
echo.
echo Install Directory: %INSTALL_DIR%
echo Test Images: %TEST_IMAGES_DIR%
echo.

REM Change to project root
cd /d "%~dp0.."

REM ============================================================================
REM STEP 1: Run Unit Tests
REM ============================================================================
echo.
echo [1/5] Running unit tests...
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found at .venv
    echo Please run setup.bat first
    exit /b 1
)

REM Run pytest with simpler output capture
.venv\Scripts\python.exe -m pytest pytest_tests -v --tb=short -p no:cacheprovider 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Unit tests failed!
    echo Please fix test failures before deploying.
    echo.
    exit /b 1
)

echo.
echo ✓ Unit tests passed
echo.

REM ============================================================================
REM STEP 2: Build Executable
REM ============================================================================
echo.
echo [2/5] Building executable...
echo.

call "%~dp0build_idt.bat"
if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    exit /b 1
)

echo.
echo ✓ Build completed
echo.

REM ============================================================================
REM STEP 3: Deploy to Installation Directory
REM ============================================================================
echo.
echo [3/5] Deploying to %INSTALL_DIR%...
echo.

REM Check if dist\idt.exe exists
if not exist "dist\idt.exe" (
    echo ERROR: Built executable not found at dist\idt.exe
    exit /b 1
)

REM Create install directory if it doesn't exist
if not exist "%INSTALL_DIR%" (
    echo Creating installation directory: %INSTALL_DIR%
    mkdir "%INSTALL_DIR%"
)

REM Copy executable
echo Copying idt.exe to %INSTALL_DIR%...
copy /Y "dist\idt.exe" "%INSTALL_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy executable
    exit /b 1
)

REM Copy scripts directory
echo Copying scripts to %INSTALL_DIR%\scripts...
if not exist "%INSTALL_DIR%\scripts" mkdir "%INSTALL_DIR%\scripts"
xcopy /Y /Q "scripts\*" "%INSTALL_DIR%\scripts\" >nul
if errorlevel 1 (
    echo WARNING: Some script files may not have copied
)

REM Copy bat files
echo Copying batch files to %INSTALL_DIR%\bat...
if not exist "%INSTALL_DIR%\bat" mkdir "%INSTALL_DIR%\bat"
xcopy /Y /Q "bat\*.bat" "%INSTALL_DIR%\bat\" >nul

echo.
echo ✓ Deployment completed
echo.

REM ============================================================================
REM STEP 4: Run Validation Workflow
REM ============================================================================
echo.
echo [4/5] Running validation workflow on frozen executable...
echo.

REM Check if test images exist
if not exist "%TEST_IMAGES_DIR%" (
    echo WARNING: Test images directory not found: %TEST_IMAGES_DIR%
    echo Skipping validation workflow
    goto :skip_validation
)

REM Count test images
set IMAGE_COUNT=0
for %%F in ("%TEST_IMAGES_DIR%\*.jpg" "%TEST_IMAGES_DIR%\*.png" "%TEST_IMAGES_DIR%\*.jpeg") do (
    set /a IMAGE_COUNT+=1
)

if %IMAGE_COUNT%==0 (
    echo WARNING: No test images found in %TEST_IMAGES_DIR%
    echo Skipping validation workflow
    goto :skip_validation
)

echo Found %IMAGE_COUNT% test images
echo.

REM Generate unique workflow name with timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%
set WORKFLOW_NAME=ValidationRun_%TIMESTAMP%

echo Running workflow: %WORKFLOW_NAME%
echo.

REM Run the workflow with geocoding enabled
cd /d "%INSTALL_DIR%"
idt.exe workflow "%TEST_IMAGES_DIR%" ^
    --output-dir Descriptions ^
    --name %WORKFLOW_NAME% ^
    --steps describe,html ^
    --provider ollama ^
    --model moondream:latest ^
    --prompt-style narrative ^
    --batch ^
    --metadata ^
    --geocode

if errorlevel 1 (
    echo.
    echo ERROR: Validation workflow failed!
    exit /b 1
)

echo.
echo ✓ Validation workflow completed
echo.

REM ============================================================================
REM STEP 5: Verify Results
REM ============================================================================
echo.
echo [5/5] Verifying results...
echo.

REM Find the workflow directory
set WORKFLOW_DIR=
for /f "delims=" %%D in ('dir /b /ad /o-d "%INSTALL_DIR%\Descriptions\wf_%WORKFLOW_NAME%*" 2^>nul') do (
    set WORKFLOW_DIR=%INSTALL_DIR%\Descriptions\%%D
    goto :found_workflow
)

:found_workflow
if "%WORKFLOW_DIR%"=="" (
    echo ERROR: Could not find workflow output directory
    exit /b 1
)

echo Workflow directory: %WORKFLOW_DIR%
echo.

REM Check for errors in log
echo Checking logs for errors...
findstr /C:"Invalid format string" /C:"KeyError" /C:"ValueError" "%WORKFLOW_DIR%\logs\*.log" >nul 2>&1
if not errorlevel 1 (
    echo.
    echo WARNING: Found errors in logs!
    echo Please review: %WORKFLOW_DIR%\logs\
    echo.
)

REM Check if descriptions were generated
if not exist "%WORKFLOW_DIR%\descriptions\image_descriptions.txt" (
    echo ERROR: image_descriptions.txt not found
    exit /b 1
)

REM Count descriptions
set DESC_COUNT=0
for /f %%L in ('find /c "File:" "%WORKFLOW_DIR%\descriptions\image_descriptions.txt"') do set DESC_COUNT=%%L

echo Found %DESC_COUNT% image descriptions
echo.

REM Check for geocoding (look for city/state names in descriptions)
findstr /R /C:"[A-Z][a-z]*, [A-Z][A-Z] [0-9]" "%WORKFLOW_DIR%\descriptions\image_descriptions.txt" >nul 2>&1
if not errorlevel 1 (
    echo ✓ Geocoding appears to be working (found city, state patterns)
) else (
    echo ⚠ Geocoding may not be working (no city, state patterns found)
)

REM Check for geocode cache file
if exist "%WORKFLOW_DIR%\geocode_cache.json" (
    echo ✓ Geocode cache file created
) else (
    echo ⚠ Geocode cache file not found
)

echo.
echo ============================================================================
echo Pipeline Complete!
echo ============================================================================
echo.
echo Summary:
echo   - Tests: PASSED
echo   - Build: SUCCESS
echo   - Deploy: SUCCESS  
echo   - Validation: %DESC_COUNT% descriptions generated
echo   - Location: %WORKFLOW_DIR%
echo.
echo Review results at: %WORKFLOW_DIR%\descriptions\image_descriptions.txt
echo.

:skip_validation
echo.
echo Done!
echo.

endlocal
exit /b 0
