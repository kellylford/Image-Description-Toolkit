@echo off
REM ============================================================================
REM Package All Applications - Master Packaging Script
REM ============================================================================
REM This script creates distribution packages for all four applications:
REM   1. IDT (main command-line toolkit)
REM   2. Viewer (image description viewer GUI)
REM   3. Prompt Editor (prompt configuration GUI)
REM   4. ImageDescriber (batch processing GUI)
REM
REM Prerequisites:
REM   - All applications built (run builditall.bat first)
REM
REM Output (all in releases/ directory):
REM   - releases/ImageDescriptionToolkit_v[VERSION].zip
REM   - releases/viewer_v[VERSION]_[ARCH].zip
REM   - releases/prompt_editor_v[VERSION]_[ARCH].zip
REM   - releases/imagedescriber_v[VERSION]_[ARCH].zip
REM ============================================================================

echo.
echo ========================================================================
echo PACKAGE ALL APPLICATIONS
echo ========================================================================
echo.
echo This will create distribution packages for all four applications.
echo All packages will be placed in the releases/ directory.
echo.

set PACKAGE_ERRORS=0

REM Create main releases directory if it doesn't exist
if not exist "releases" mkdir releases

REM ============================================================================
echo.
echo [1/4] Packaging IDT (main toolkit)...
echo ========================================================================
echo.

call package_idt.bat
if errorlevel 1 (
    echo ERROR: IDT packaging failed!
    set /a PACKAGE_ERRORS+=1
) else (
    echo SUCCESS: IDT packaged successfully
)

REM ============================================================================
echo.
echo [2/4] Packaging Viewer...
echo ========================================================================
echo.

cd viewer
call package_viewer.bat
if errorlevel 1 (
    echo ERROR: Viewer packaging failed!
    set /a PACKAGE_ERRORS+=1
) else (
    echo SUCCESS: Viewer packaged successfully
    REM Move viewer package to main releases directory
    if exist "viewer_releases\*.zip" (
        echo Moving viewer package to releases\...
        move /Y "viewer_releases\*.zip" "..\releases\" >nul
        if errorlevel 1 (
            echo WARNING: Failed to move viewer package
        ) else (
            echo Viewer package moved to releases\
        )
    )
)
cd ..

REM ============================================================================
echo.
echo [3/4] Packaging Prompt Editor...
echo ========================================================================
echo.

cd prompt_editor
call package_prompt_editor.bat
if errorlevel 1 (
    echo ERROR: Prompt Editor packaging failed!
    set /a PACKAGE_ERRORS+=1
) else (
    echo SUCCESS: Prompt Editor packaged successfully
    REM Move prompt_editor package to main releases directory
    if exist "prompt_editor_releases\*.zip" (
        echo Moving prompt editor package to releases\...
        move /Y "prompt_editor_releases\*.zip" "..\releases\" >nul
        if errorlevel 1 (
            echo WARNING: Failed to move prompt editor package
        ) else (
            echo Prompt editor package moved to releases\
        )
    )
)
cd ..

REM ============================================================================
echo.
echo [4/4] Packaging ImageDescriber...
echo ========================================================================
echo.

cd imagedescriber
call package_imagedescriber.bat
if errorlevel 1 (
    echo ERROR: ImageDescriber packaging failed!
    set /a PACKAGE_ERRORS+=1
) else (
    echo SUCCESS: ImageDescriber packaged successfully
    REM Move imagedescriber package to main releases directory
    if exist "imagedescriber_releases\*.zip" (
        echo Moving imagedescriber package to releases\...
        move /Y "imagedescriber_releases\*.zip" "..\releases\" >nul
        if errorlevel 1 (
            echo WARNING: Failed to move imagedescriber package
        ) else (
            echo ImageDescriber package moved to releases\
        )
    )
)
cd ..

REM ============================================================================
echo.
echo ========================================================================
echo PACKAGING SUMMARY
echo ========================================================================
echo.

if %PACKAGE_ERRORS%==0 (
    echo SUCCESS: All applications packaged successfully!
    echo.
    echo Distribution packages in releases\ directory:
    dir /b releases\*.zip 2>nul
    echo.
    echo All packages are ready for distribution!
) else (
    echo ERRORS ENCOUNTERED: %PACKAGE_ERRORS% packaging operation(s) failed
    echo Please review the output above for error details.
)

echo.
echo ========================================================================
echo RELEASE DIRECTORY CONTENTS
echo ========================================================================
echo.
if exist "releases" (
    dir releases\*.zip
) else (
    echo No releases directory found.
)

echo.
