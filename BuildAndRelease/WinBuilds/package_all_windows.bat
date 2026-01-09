@echo off
REM ============================================================================
REM Package All Applications for Windows
REM ============================================================================
REM Collects all built executables into BuildAndRelease\dist_all directory
REM Prerequisites: Run builditall_wx.bat first
REM ============================================================================

echo.
echo ========================================================================
echo PACKAGE ALL APPLICATIONS (Windows)
echo ========================================================================
echo.

cd /d "%~dp0"

REM Create output directory
if not exist "dist_all" mkdir dist_all
if not exist "dist_all\bin" mkdir dist_all\bin

REM Clean old files
echo Cleaning old package...
del /Q dist_all\bin\*.exe 2>nul
del /Q dist_all\*.md 2>nul
del /Q dist_all\*.txt 2>nul

REM Copy IDT CLI
echo Copying IDT CLI...
if exist "..\..\idt\dist\idt.exe" (
    copy /Y "..\..\idt\dist\idt.exe" "dist_all\bin\" >nul
    echo   ✓ idt.exe
) else (
    echo   ✗ idt.exe NOT FOUND
)

REM Copy Viewer
echo Copying Viewer...
if exist "..\..\viewer\dist\Viewer.exe" (
    copy /Y "..\..\viewer\dist\Viewer.exe" "dist_all\bin\" >nul
    echo   ✓ Viewer.exe
) else (
    echo   ✗ Viewer.exe NOT FOUND
)

REM Copy Prompt Editor
echo Copying Prompt Editor...
if exist "..\..\prompt_editor\dist\PromptEditor.exe" (
    copy /Y "..\..\prompt_editor\dist\PromptEditor.exe" "dist_all\bin\" >nul
    echo   ✓ PromptEditor.exe
) else (
    echo   ✗ PromptEditor.exe NOT FOUND
)

REM Copy ImageDescriber
echo Copying ImageDescriber...
if exist "..\..\imagedescriber\dist\ImageDescriber.exe" (
    copy /Y "..\..\imagedescriber\dist\ImageDescriber.exe" "dist_all\bin\" >nul
    echo   ✓ ImageDescriber.exe
) else (
    echo   ✗ ImageDescriber.exe NOT FOUND
)

REM Copy IDTConfigure
echo Copying IDTConfigure...
if exist "..\..\idtconfigure\dist\IDTConfigure.exe" (
    copy /Y "..\..\idtconfigure\dist\IDTConfigure.exe" "dist_all\bin\" >nul
    echo   ✓ IDTConfigure.exe
) else (
    echo   ✗ IDTConfigure.exe NOT FOUND
)

REM Copy documentation
echo.
echo Copying documentation...
if exist "..\..\README.md" copy /Y "..\..\README.md" "dist_all\" >nul
if exist "..\..\LICENSE" copy /Y "..\..\LICENSE" "dist_all\" >nul
if exist "..\..\install_idt.bat" copy /Y "..\..\install_idt.bat" "dist_all\" >nul

echo.
echo ========================================================================
echo PACKAGING COMPLETE
echo ========================================================================
echo.
echo All executables packaged in: BuildAndRelease\dist_all\bin\
echo.
echo Ready for distribution or installer creation.
echo.
