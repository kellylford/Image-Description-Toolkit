@echo off
REM ============================================================================
REM Build All wxPython Applications for Windows
REM ============================================================================
REM This script builds both wxPython-based applications:
REM   1. IDT (CLI - no GUI framework)
REM   2. ImageDescriber (wxPython - includes integrated Viewer Mode, PromptEditor, and IDTConfigure)
REM
REM NOTE: Uses .winenv virtual environments (created by winsetup.bat)
REM       This allows .venv (macOS) and .winenv (Windows) to coexist
REM ============================================================================

echo.
echo ========================================================================
echo BUILD ALL wxPython APPLICATIONS (Windows)
echo ========================================================================
echo This script builds ImageDescriber.
echo Viewer is now integrated into ImageDescriber (Viewer Mode).
echo.

REM Save current directory (should be BuildAndRelease\WinBuilds)
set "ORIGINAL_DIR=%CD%"

cd /d "%~dp0..\.."

set BUILD_ERRORS=0

REM ============================================================================
REM Delete last build's executables first. Without this, a failed build leaves
REM the previous run's exe in dist\ and the packaging step below happily ships
REM it -- a stale binary in an installer that reports success.
REM ============================================================================
if exist "idt\dist\idt.exe" del /Q "idt\dist\idt.exe"
if exist "imagedescriber\dist\ImageDescriber.exe" del /Q "imagedescriber\dist\ImageDescriber.exe"

REM ============================================================================
echo [1/2] Building IDT (CLI)...
echo ========================================================================
echo.
echo.

cd idt
REM ".\" prefix: resolves even when NoDefaultCurrentDirectoryInExePath is set.
call .\build_idt.bat
if errorlevel 1 (
    echo ERROR: IDT build failed!
    set /a BUILD_ERRORS+=1
) else (
    echo SUCCESS: IDT built successfully
)
cd ..

REM ============================================================================
echo.
echo [2/2] Building ImageDescriber (wxPython - includes Viewer Mode + PromptEditor + IDTConfigure)...
echo ========================================================================
echo.

cd imagedescriber
call .\build_imagedescriber_wx.bat
if errorlevel 1 (
    echo ERROR: ImageDescriber build failed!
    set /a BUILD_ERRORS+=1
) else (
    echo SUCCESS: ImageDescriber built successfully
)
cd ..

REM ============================================================================
echo.
echo ========================================================================
echo BUILD SUMMARY
echo ========================================================================
echo.

REM ============================================================================
REM Everything below runs at TOP LEVEL. Nothing that decides the exit code may
REM live inside a parenthesised block that is nested inside another one.
REM
REM cmd DISCARDS the exit code of "exit /b N" issued from an if-block that is
REM itself inside an if-block. The script does terminate and does print its
REM error, but the caller is told the run succeeded. One level of nesting is
REM fine; two is not:
REM
REM     if "%E%"=="0" ( if not exist x ( exit /b 1 ) )    -- caller sees 0
REM     if "%E%"=="0" ( exit /b 1 )                       -- caller sees 1
REM
REM That is why the missing-artifact guards added in 1488bb5 could not fail a
REM build: they printed "NOT FOUND" and still exited 0, so a sub-build that
REM emitted nothing was packaged anyway and the run looked clean. Same defect
REM class as the unescaped-paren bug, different mechanism. Verified 2026-07-28.
REM
REM Flat control flow with goto has no such trap.
REM pytest_tests/unit/test_build_orchestrators.py runs these paths for real.
REM ============================================================================

if not "%BUILD_ERRORS%"=="0" goto :builds_failed

echo SUCCESS: All wxPython applications built successfully!
echo.
echo ========================================================================
echo PACKAGING ALL APPLICATIONS
echo ========================================================================
echo.

REM Create distribution directory in BuildAndRelease\WinBuilds
if not exist "BuildAndRelease\WinBuilds\dist_all" mkdir BuildAndRelease\WinBuilds\dist_all
if not exist "BuildAndRelease\WinBuilds\dist_all\bin" mkdir BuildAndRelease\WinBuilds\dist_all\bin

REM Clean old files
echo Cleaning old package...
del /Q BuildAndRelease\WinBuilds\dist_all\bin\*.exe 2>nul
del /Q BuildAndRelease\WinBuilds\dist_all\*.md 2>nul
del /Q BuildAndRelease\WinBuilds\dist_all\*.txt 2>nul

echo Packaging applications...
echo.

REM Copy IDT CLI. A missing exe is fatal: never package a partial build.
if not exist "idt\dist\idt.exe" goto :missing_idt
copy /Y "idt\dist\idt.exe" "BuildAndRelease\WinBuilds\dist_all\bin\" >nul
if errorlevel 1 goto :copy_failed_idt
echo   ✓ idt.exe

REM Copy ImageDescriber (includes Viewer Mode, PromptEditor and IDTConfigure)
if not exist "imagedescriber\dist\ImageDescriber.exe" goto :missing_describer
copy /Y "imagedescriber\dist\ImageDescriber.exe" "BuildAndRelease\WinBuilds\dist_all\bin\" >nul
if errorlevel 1 goto :copy_failed_describer
echo   ✓ ImageDescriber.exe ^(with integrated Viewer Mode and tools^)

REM Copy documentation
echo.
echo Copying documentation...
if exist "README.md" copy /Y "README.md" "BuildAndRelease\WinBuilds\dist_all\" >nul
if exist "LICENSE" copy /Y "LICENSE" "BuildAndRelease\WinBuilds\dist_all\" >nul

echo.
echo ========================================================================
echo PACKAGING COMPLETE
echo ========================================================================
echo.
echo All applications packaged in: BuildAndRelease\WinBuilds\dist_all\bin\
echo.
echo Ready for distribution or installer creation.
echo.
echo Next step: Run build_installer.bat to create Windows installer

REM Return to original directory
cd /d "%ORIGINAL_DIR%"
exit /b 0

REM ---------------------------------------------------------------------------
REM Failure exits. Each is at top level, so its code actually reaches the caller.
REM ---------------------------------------------------------------------------

:missing_idt
echo   ✗ idt.exe NOT FOUND - the build did not produce an executable
cd /d "%ORIGINAL_DIR%"
exit /b 1

:copy_failed_idt
echo   ✗ idt.exe could not be copied into dist_all\bin
cd /d "%ORIGINAL_DIR%"
exit /b 1

:missing_describer
echo   ✗ ImageDescriber.exe NOT FOUND - the build did not produce an executable
cd /d "%ORIGINAL_DIR%"
exit /b 1

:copy_failed_describer
echo   ✗ ImageDescriber.exe could not be copied into dist_all\bin
cd /d "%ORIGINAL_DIR%"
exit /b 1

:builds_failed
echo ERRORS: %BUILD_ERRORS% build failures encountered
echo.
echo If .winenv errors, run: winsetup.bat
cd /d "%ORIGINAL_DIR%"
exit /b 1
