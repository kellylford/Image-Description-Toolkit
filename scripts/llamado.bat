@echo off
REM Usage: llamado.bat <model> <image_directory> <prompt>
REM Example: llamado.bat llava "C:\images" "Describe this image"

setlocal enabledelayedexpansion

set "MODEL=%~1"
set "IMGDIR=%~2"
set "PROMPT=%~3"
set "OUTFILE=ollama_output.txt"

if "%MODEL%"=="" (
    echo Error: Model name required.
    echo Usage: llamado.bat ^<model^> ^<image_directory^> ^<prompt^>
    exit /b 1
)
if "%IMGDIR%"=="" (
    echo Error: Image directory required.
    echo Usage: llamado.bat ^<model^> ^<image_directory^> ^<prompt^>
    exit /b 1
)
if "%PROMPT%"=="" (
    echo Error: Prompt required.
    echo Usage: llamado.bat ^<model^> ^<image_directory^> ^<prompt^>
    exit /b 1
)

REM Clear output file
> "%OUTFILE%" echo Ollama Image Analysis Output - %date% %time%
echo Starting batch processing with model: %MODEL%
echo Processing directory: %IMGDIR%
echo Using prompt: %PROMPT%
echo ====================================

REM Recursively loop through images
for /r "%IMGDIR%" %%F in (*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff *.tif) do (
    echo Processing: %%F
    echo. >> "%OUTFILE%"
    echo ====================================== >> "%OUTFILE%"
    echo File: %%F >> "%OUTFILE%"
    echo ====================================== >> "%OUTFILE%"
    ollama run %MODEL% "%PROMPT% [image:%%F]" >> "%OUTFILE%"
    echo. >> "%OUTFILE%"
)

echo Done! Output saved to %OUTFILE%
endlocal
