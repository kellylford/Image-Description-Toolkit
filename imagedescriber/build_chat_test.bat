@echo off
REM Quick build script for testing chat feature

echo Activating virtual environment...
call .winenv\Scripts\activate.bat

echo.
echo Building ImageDescriber with chat feature...
python -m PyInstaller imagedescriber_wx.spec --clean --noconfirm

echo.
echo Build complete!
echo Executable location: dist\ImageDescriber.exe
echo.
pause
