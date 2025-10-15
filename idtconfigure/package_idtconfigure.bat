@echo off
REM Package IDT Configure for distribution
REM Creates a ZIP file with executable and documentation

echo ========================================
echo Packaging IDT Configure
echo ========================================
echo.

REM Get version
set /p VERSION=<..\VERSION

REM Check if executable exists
if not exist "dist\idtconfigure\idtconfigure.exe" (
    echo ERROR: idtconfigure.exe not found!
    echo.
    echo Please run build_idtconfigure.bat first
    echo.
    pause
    exit /b 1
)

REM Set package name
set ZIP_NAME=idtconfigure_v%VERSION%.zip

echo Version: %VERSION%
echo Package: %ZIP_NAME%
echo.

REM Create package directory
if exist package rmdir /s /q package
mkdir package\idtconfigure

echo Copying files...

REM Copy executable and dependencies
xcopy /E /I /Y "dist\idtconfigure\*" "package\idtconfigure\" > nul

REM Create README
echo Creating README...
(
echo IDT Configure - Configuration Manager
echo =====================================
echo.
echo Version: %VERSION%
echo.
echo DESCRIPTION
echo -----------
echo IDT Configure is a graphical configuration manager for the Image Description
echo Toolkit. It provides an easy-to-use interface for adjusting all configuration
echo settings without manually editing JSON files.
echo.
echo FEATURES
echo --------
echo - AI Model Settings: temperature, tokens, and other parameters
echo - Prompt Styles: Choose default description styles
echo - Video Extraction: Configure frame extraction modes
echo - Processing Options: Adjust memory, delays, and optimization
echo - Workflow Settings: Enable/disable workflow steps
echo - Output Format: Control output file contents
echo - Full keyboard accessibility
echo - Menu-based navigation
echo.
echo REQUIREMENTS
echo ------------
echo - Windows 10 or later
echo - No Python installation required ^(standalone executable^)
echo.
echo INSTALLATION
echo ------------
echo 1. Extract this ZIP file to a directory of your choice
echo 2. Run idtconfigure.exe
echo.
echo USAGE
echo -----
echo 1. Start idtconfigure.exe
echo 2. Select a category from the Settings menu
echo 3. Navigate settings with arrow keys
echo 4. Press "Change Setting" button or Enter to edit
echo 5. Use File -^> Save All to save changes ^(Ctrl+S^)
echo.
echo KEYBOARD SHORTCUTS
echo ------------------
echo Ctrl+R : Reload configurations from disk
echo Ctrl+S : Save all changes
echo F1     : Help
echo Alt+F  : File menu
echo Alt+S  : Settings menu
echo.
echo CONFIGURATION FILES
echo -------------------
echo IDT Configure manages these configuration files in the scripts/ directory:
echo - image_describer_config.json     : AI model and description settings
echo - video_frame_extractor_config.json : Video frame extraction settings
echo - workflow_config.json            : Workflow step configuration
echo.
echo ACCESSIBILITY
echo -------------
echo This application is fully accessible:
echo - Screen reader compatible
echo - Full keyboard navigation
echo - Clear focus indicators
echo - Descriptive labels and help text
echo.
echo TIPS
echo ----
echo - Changes are not saved until you use File -^> Save All
echo - You can export/import configurations for backup or sharing
echo - Each setting includes a detailed explanation
echo - Use Ctrl+R to reload if you edit config files manually
echo.
echo DOCUMENTATION
echo -------------
echo For more information, see the main IDT documentation:
echo https://github.com/kellylford/Image-Description-Toolkit
echo.
echo LICENSE
echo -------
echo Same license as Image Description Toolkit
echo.
echo SUPPORT
echo -------
echo For issues or questions:
echo https://github.com/kellylford/Image-Description-Toolkit/issues
) > "package\idtconfigure\README.txt"

REM Create quick start guide
(
echo IDT Configure - Quick Start
echo ===========================
echo.
echo 1. LAUNCH
echo    Double-click idtconfigure.exe
echo.
echo 2. CHOOSE CATEGORY
echo    Settings menu -^> Select category
echo    ^(AI Model Settings, Video Extraction, etc.^)
echo.
echo 3. NAVIGATE SETTINGS
echo    Use Up/Down arrow keys
echo    Or click with mouse
echo.
echo 4. CHANGE A SETTING
echo    Press "Change Setting" button
echo    Or press Enter key
echo    Adjust the value
echo    Click OK
echo.
echo 5. SAVE CHANGES
echo    File menu -^> Save All
echo    Or press Ctrl+S
echo.
echo IMPORTANT
echo ---------
echo Changes are NOT automatically saved!
echo You must use File -^> Save All to persist changes.
echo.
echo CATEGORIES
echo ----------
echo AI Model Settings  : Temperature, tokens, repeat penalty
echo Prompt Styles      : Default prompt style selection
echo Video Extraction   : Time interval vs scene change mode
echo Processing Options : Memory, batch delay, compression
echo Workflow Settings  : Enable/disable workflow steps
echo Output Format      : What to include in output files
echo.
echo HELP
echo ----
echo Press F1 or Help menu -^> Help for detailed information
) > "package\idtconfigure\QUICK_START.txt"

REM Create the ZIP file
echo.
echo Creating ZIP package...

REM Check for 7-Zip
where 7z >nul 2>nul
if %errorlevel% equ 0 (
    echo Using 7-Zip...
    cd package
    7z a -tzip "..\%ZIP_NAME%" idtconfigure\ > nul
    cd ..
    goto :package_done
)

REM Check for PowerShell (Windows 10+)
powershell -Command "Get-Command Compress-Archive" >nul 2>nul
if %errorlevel% equ 0 (
    echo Using PowerShell...
    powershell -NoProfile -Command "Compress-Archive -Path 'package\idtconfigure\*' -DestinationPath '%ZIP_NAME%' -Force"
    goto :package_done
)

REM No compression tool found
echo.
echo WARNING: No compression tool found!
echo Install 7-Zip or use Windows 10+ PowerShell
echo.
echo Files are ready in package\idtconfigure\
echo Please create ZIP manually
goto :end

:package_done
echo.
echo Cleaning up...
rmdir /s /q package

echo.
echo ========================================
echo Package created successfully!
echo ========================================
echo.
echo Package: %ZIP_NAME%
echo Size:
dir /b "%ZIP_NAME%" | findstr /r ".*"
for %%A in (%ZIP_NAME%) do echo    %%~zA bytes
echo.
echo Ready for distribution!
echo.

:end
pause
