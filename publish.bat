@echo off
REM ============================================================================
REM Public Build and Deployment Script
REM ============================================================================
REM This script automates the complete build and deployment process:
REM 1. Builds the executable
REM 2. Creates distribution package
REM 3. Cleans idtexternal\idt (preserving Descriptions)
REM 4. Unpacks new distribution to idtexternal\idt for testing
REM ============================================================================

echo.
echo ========================================================================
echo Image Description Toolkit - Complete Build and Deploy
echo ========================================================================
echo.

REM Store current directory
set PROJECT_ROOT=%CD%

REM Step 1: Build the executable
echo [1/4] Building executable...
echo.
call build.bat
if errorlevel 1 (
    echo ERROR: Build failed!
    pause
     exit /b 1
 )

echo.
echo [Build completed successfully]
echo.

REM Step 2: Create distribution package
echo [2/4] Creating distribution package...
echo.
call create_distribution.bat
if errorlevel 1 (
    echo ERROR: Distribution creation failed!
    pause
    exit /b 1
)

echo.
echo [Distribution package created successfully]
echo.

REM Step 3: Clean idtexternal\idt (preserve Descriptions)
echo [3/4] Cleaning idtexternal\idt directory...
echo.

REM Check if idtexternal\idt exists
if not exist "idtexternal\idt" (
    echo Creating idtexternal\idt directory...
    mkdir "idtexternal\idt"
    goto :skip_clean
)

REM Preserve Descriptions directory if it exists
set TEMP_DESC_DIR=%TEMP%\idt_descriptions_backup_%RANDOM%
if exist "idtexternal\idt\Descriptions" (
    echo Backing up Descriptions directory...
    move "idtexternal\idt\Descriptions" "%TEMP_DESC_DIR%" >nul
    if errorlevel 1 (
        echo WARNING: Could not backup Descriptions directory
    )
)

REM Clean the directory
echo Removing old files from idtexternal\idt...
for /d %%i in ("idtexternal\idt\*") do (
    if /i not "%%~ni"=="Descriptions" (
        rmdir /s /q "%%i" 2>nul
    )
)
for %%i in ("idtexternal\idt\*") do (
    del /q "%%i" 2>nul
)

REM Restore Descriptions directory
if exist "%TEMP_DESC_DIR%" (
    echo Restoring Descriptions directory...
    move "%TEMP_DESC_DIR%" "idtexternal\idt\Descriptions" >nul
    if errorlevel 1 (
        echo WARNING: Could not restore Descriptions directory
    )
)

:skip_clean
echo [Directory cleaned successfully]
echo.

REM Step 4: Unpack distribution to idtexternal\idt
echo [4/4] Unpacking distribution to idtexternal\idt...
echo.

REM Get version for zip filename
set VERSION=unknown
if exist "VERSION" (
    set /p VERSION=<VERSION
)

set ZIP_FILE=releases\ImageDescriptionToolkit_v%VERSION%.zip

if not exist "%ZIP_FILE%" (
    echo ERROR: Distribution zip file not found: %ZIP_FILE%
    echo.
    echo Expected location: %PROJECT_ROOT%\%ZIP_FILE%
    pause
    exit /b 1
)

REM Extract zip file to idtexternal\idt
echo Extracting %ZIP_FILE% to idtexternal\idt...
powershell -command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath 'idtexternal\idt'"
if errorlevel 1 (
    echo ERROR: Failed to extract distribution package
    pause
    exit /b 1
)

echo [Distribution unpacked successfully]

REM Verify Descriptions directory was preserved
if exist "idtexternal\idt\Descriptions" (
    echo [Descriptions directory preserved successfully]
) else (
    echo WARNING: Descriptions directory was not preserved
)
echo.

REM Final step: Copy to OneDrive (original functionality)
echo [Bonus] Copying to OneDrive...
del /q c:\users\kelly\onedrive\idt\ImageDescriptionToolkit_v%VERSION%.zip 2>nul
copy "%ZIP_FILE%" c:\users\kelly\onedrive\idt\
if errorlevel 1 (
    echo WARNING: Could not copy to OneDrive location
) else (
    echo [OneDrive copy completed]
)

echo.
echo ========================================================================
echo BUILD AND DEPLOYMENT COMPLETE
echo ========================================================================
echo.
echo Summary:
echo   - Executable built: dist\idt.exe
echo   - Distribution created: %ZIP_FILE%
echo   - Testing environment ready: idtexternal\idt\
echo   - OneDrive copy: c:\users\kelly\onedrive\idt\
echo.
echo You can now test the deployment in idtexternal\idt\
echo.
pause
