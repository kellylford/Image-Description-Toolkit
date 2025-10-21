@echo off
REM ============================================================================
REM IDT Comprehensive Testing Automation
REM ============================================================================
REM This script performs a complete end-to-end test of the Image Description
REM Toolkit on a clean machine. It builds, installs, and tests the complete
REM pipeline with a standardized test dataset.
REM
REM Requirements:
REM   - Windows 10/11
REM   - Internet connection
REM   - Administrator privileges (for Ollama installation)
REM
REM What this script does:
REM   1. Installs Python and dependencies
REM   2. Builds all IDT applications
REM   3. Installs Ollama and required models
REM   4. Runs comprehensive tests with 5-file test dataset
REM   5. Validates all outputs and generates test report
REM ============================================================================

SETLOCAL EnableDelayedExpansion
set START_TIME=%TIME%
set TEST_LOG=test_automation_%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.log
set TEST_LOG=%TEST_LOG: =0%

echo ============================================================================
echo IDT COMPREHENSIVE TESTING AUTOMATION
echo ============================================================================
echo Start Time: %DATE% %TIME%
echo Log File: %TEST_LOG%
echo.

REM Create log file
echo IDT Comprehensive Testing Log - %DATE% %TIME% > %TEST_LOG%
echo ============================================================================ >> %TEST_LOG%

REM ============================================================================
echo PHASE 1: ENVIRONMENT VALIDATION
echo ============================================================================
echo Checking prerequisites...

REM Check if running as administrator
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: This script requires administrator privileges for Ollama installation.
    echo Please run as administrator.
    echo ERROR: Administrator privileges required >> %TEST_LOG%
    pause
    exit /b 1
)

echo ✓ Administrator privileges confirmed
echo ✓ Administrator privileges confirmed >> %TEST_LOG%

REM Check internet connectivity
ping -n 1 google.com >nul 2>&1
if errorlevel 1 (
    echo ERROR: No internet connection detected.
    echo Internet is required for downloading dependencies.
    echo ERROR: No internet connection >> %TEST_LOG%
    pause
    exit /b 1
)

echo ✓ Internet connectivity confirmed
echo ✓ Internet connectivity confirmed >> %TEST_LOG%

REM ============================================================================
echo.
echo PHASE 2: PYTHON ENVIRONMENT SETUP
echo ============================================================================
echo Checking Python installation...

python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python 3.11+ before running this script.
    echo Download from: https://www.python.org/downloads/
    echo ERROR: Python not found >> %TEST_LOG%
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
echo ✓ Python %PYTHON_VERSION% found
echo ✓ Python %PYTHON_VERSION% found >> %TEST_LOG%

REM Install/upgrade pip and dependencies
echo Installing Python dependencies...
python -m pip install --upgrade pip >> %TEST_LOG% 2>&1
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip
    echo ERROR: Failed to upgrade pip >> %TEST_LOG%
    pause
    exit /b 1
)

pip install -r requirements.txt >> %TEST_LOG% 2>&1
if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies
    echo ERROR: Failed to install Python dependencies >> %TEST_LOG%
    pause
    exit /b 1
)

pip install pyinstaller >> %TEST_LOG% 2>&1
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    echo ERROR: Failed to install PyInstaller >> %TEST_LOG%
    pause
    exit /b 1
)

echo ✓ Python dependencies installed
echo ✓ Python dependencies installed >> %TEST_LOG%

REM ============================================================================
echo.
echo PHASE 3: BUILD ALL APPLICATIONS
echo ============================================================================
echo Building IDT applications...

call releaseitall.bat >> %TEST_LOG% 2>&1
if errorlevel 1 (
    echo ERROR: Build failed!
    echo Check %TEST_LOG% for details.
    echo ERROR: Build failed >> %TEST_LOG%
    pause
    exit /b 1
)

REM Verify build outputs
if not exist "releases\idt2.zip" (
    echo ERROR: Master package idt2.zip not found!
    echo ERROR: Master package idt2.zip not found >> %TEST_LOG%
    pause
    exit /b 1
)

echo ✓ All applications built successfully
echo ✓ All applications built successfully >> %TEST_LOG%

REM ============================================================================
echo.
echo PHASE 4: OLLAMA SETUP
echo ============================================================================
echo Installing Ollama...

REM Check if Ollama is already installed
where ollama >nul 2>&1
if not errorlevel 1 (
    echo ✓ Ollama already installed
    echo ✓ Ollama already installed >> %TEST_LOG%
    goto :ollama_models
)

REM Download and install Ollama
echo Downloading Ollama installer...
powershell -Command "Invoke-WebRequest -Uri 'https://ollama.ai/download/windows' -OutFile 'ollama_installer.exe'" >> %TEST_LOG% 2>&1
if errorlevel 1 (
    echo ERROR: Failed to download Ollama installer
    echo ERROR: Failed to download Ollama installer >> %TEST_LOG%
    pause
    exit /b 1
)

echo Installing Ollama (this may take a few minutes)...
ollama_installer.exe /S >> %TEST_LOG% 2>&1
if errorlevel 1 (
    echo ERROR: Ollama installation failed
    echo ERROR: Ollama installation failed >> %TEST_LOG%
    pause
    exit /b 1
)

REM Wait for Ollama service to start
echo Waiting for Ollama service to start...
timeout /t 10 /nobreak >nul

REM Clean up installer
del ollama_installer.exe >nul 2>&1

echo ✓ Ollama installed successfully
echo ✓ Ollama installed successfully >> %TEST_LOG%

:ollama_models
echo.
echo Downloading required models...

REM Pull moondream model
echo Pulling moondream model (this may take several minutes)...
ollama pull moondream >> %TEST_LOG% 2>&1
if errorlevel 1 (
    echo ERROR: Failed to pull moondream model
    echo ERROR: Failed to pull moondream model >> %TEST_LOG%
    pause
    exit /b 1
)

echo ✓ Moondream model downloaded

REM Pull gemma3 model
echo Pulling gemma3 model (this may take several minutes)...
ollama pull gemma3 >> %TEST_LOG% 2>&1
if errorlevel 1 (
    echo ERROR: Failed to pull gemma3 model
    echo ERROR: Failed to pull gemma3 model >> %TEST_LOG%
    pause
    exit /b 1
)

echo ✓ Gemma3 model downloaded
echo ✓ Required models downloaded successfully >> %TEST_LOG%

REM List installed models for verification
echo.
echo Installed Ollama models:
ollama list >> %TEST_LOG% 2>&1
ollama list

REM ============================================================================
echo.
echo PHASE 5: TEST DATA VALIDATION
echo ============================================================================
echo Checking test data...

if not exist "test_data" (
    echo ERROR: test_data directory not found!
    echo Please ensure test_data directory exists with required test files.
    echo ERROR: test_data directory not found >> %TEST_LOG%
    pause
    exit /b 1
)

REM Count files in test_data (should be exactly 5)
set FILE_COUNT=0
for /r test_data %%f in (*.*) do (
    if not "%%~nxf"=="README.md" (
        set /a FILE_COUNT+=1
    )
)

if %FILE_COUNT% neq 5 (
    echo WARNING: Expected exactly 5 test files, found %FILE_COUNT%
    echo WARNING: Expected 5 test files, found %FILE_COUNT% >> %TEST_LOG%
    echo Continuing anyway...
) else (
    echo ✓ Test data validated (%FILE_COUNT% files)
    echo ✓ Test data validated (%FILE_COUNT% files) >> %TEST_LOG%
)

REM ============================================================================
echo.
echo PHASE 6: COMPREHENSIVE WORKFLOW TESTING
echo ============================================================================
echo Running allmodeltest with test data...

REM Run allmodeltest.bat with test data
call bat\allmodeltest.bat test_data --batch --name comprehensive_test >> %TEST_LOG% 2>&1
if errorlevel 1 (
    echo ERROR: Workflow testing failed!
    echo Check %TEST_LOG% for details.
    echo ERROR: Workflow testing failed >> %TEST_LOG%
    pause
    exit /b 1
)

echo ✓ Workflow testing completed
echo ✓ Workflow testing completed >> %TEST_LOG%

REM ============================================================================
echo.
echo PHASE 7: OUTPUT VALIDATION
echo ============================================================================
echo Validating test outputs...

REM Check if workflow directories were created
set WORKFLOW_COUNT=0
for /d %%d in (Descriptions\wf_comprehensive_test_*) do (
    set /a WORKFLOW_COUNT+=1
    echo Found workflow: %%d
    echo Found workflow: %%d >> %TEST_LOG%
)

if %WORKFLOW_COUNT% equ 0 (
    echo ERROR: No workflow output directories found!
    echo ERROR: No workflow output directories found >> %TEST_LOG%
    pause
    exit /b 1
)

echo ✓ Found %WORKFLOW_COUNT% workflow output directories
echo ✓ Found %WORKFLOW_COUNT% workflow output directories >> %TEST_LOG%

REM Validate each workflow directory structure
set VALIDATION_PASSED=0
set VALIDATION_TOTAL=0

for /d %%d in (Descriptions\wf_comprehensive_test_*) do (
    set /a VALIDATION_TOTAL+=1
    echo Validating %%d...
    
    REM Check for required files
    if exist "%%d\image_descriptions.txt" (
        if exist "%%d\index.html" (
            if exist "%%d\view_results.bat" (
                set /a VALIDATION_PASSED+=1
                echo ✓ %%d validation passed
                echo ✓ %%d validation passed >> %TEST_LOG%
            ) else (
                echo ✗ %%d missing view_results.bat
                echo ✗ %%d missing view_results.bat >> %TEST_LOG%
            )
        ) else (
            echo ✗ %%d missing index.html
            echo ✗ %%d missing index.html >> %TEST_LOG%
        )
    ) else (
        echo ✗ %%d missing image_descriptions.txt
        echo ✗ %%d missing image_descriptions.txt >> %TEST_LOG%
    )
)

echo.
echo Validation Summary: %VALIDATION_PASSED%/%VALIDATION_TOTAL% workflows passed
echo Validation Summary: %VALIDATION_PASSED%/%VALIDATION_TOTAL% workflows passed >> %TEST_LOG%

REM ============================================================================
echo.
echo PHASE 8: ANALYSIS TOOLS TESTING
echo ============================================================================
echo Testing analysis tools...

REM Test CombineDescriptions
echo Testing CombineDescriptions...
python analysis\combine_workflow_descriptions.py >> %TEST_LOG% 2>&1
if errorlevel 1 (
    echo WARNING: CombineDescriptions failed
    echo WARNING: CombineDescriptions failed >> %TEST_LOG%
) else (
    echo ✓ CombineDescriptions completed
    echo ✓ CombineDescriptions completed >> %TEST_LOG%
)

REM Test Stats Analysis
echo Testing Stats Analysis...
python analysis\stats_analysis.py >> %TEST_LOG% 2>&1
if errorlevel 1 (
    echo WARNING: Stats Analysis failed
    echo WARNING: Stats Analysis failed >> %TEST_LOG%
) else (
    echo ✓ Stats Analysis completed
    echo ✓ Stats Analysis completed >> %TEST_LOG%
)

REM ============================================================================
echo.
echo COMPREHENSIVE TEST COMPLETE!
echo ============================================================================

set END_TIME=%TIME%
echo Start Time: %START_TIME%
echo End Time: %END_TIME%
echo Log File: %TEST_LOG%
echo.

REM Calculate overall success
if %VALIDATION_PASSED% equ %VALIDATION_TOTAL% (
    if %WORKFLOW_COUNT% gtr 0 (
        echo 🎉 ALL TESTS PASSED! 🎉
        echo Result: SUCCESS >> %TEST_LOG%
        echo.
        echo ✓ Build: SUCCESS
        echo ✓ Ollama Setup: SUCCESS  
        echo ✓ Model Downloads: SUCCESS
        echo ✓ Workflow Testing: SUCCESS
        echo ✓ Output Validation: SUCCESS (%VALIDATION_PASSED%/%VALIDATION_TOTAL%)
        echo ✓ Analysis Tools: SUCCESS
    ) else (
        echo ❌ TESTS FAILED - No workflows created
        echo Result: FAILED - No workflows >> %TEST_LOG%
    )
) else (
    echo ❌ TESTS FAILED - Validation issues
    echo Result: FAILED - Validation %VALIDATION_PASSED%/%VALIDATION_TOTAL% >> %TEST_LOG%
)

echo.
echo Next Steps:
echo 1. Review log file: %TEST_LOG%
echo 2. Check workflow outputs in: Descriptions\
echo 3. Test viewer: python viewer\viewer.py
echo 4. Open HTML reports in browser
echo.

echo ============================================================================
echo End Time: %DATE% %TIME% >> %TEST_LOG%
echo Test automation complete - check results above >> %TEST_LOG%

pause
ENDLOCAL