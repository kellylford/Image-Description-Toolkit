@echo off
REM Launch local web server and open ImageGallery in browser
REM This allows testing the gallery locally before deploying to web server

echo ========================================
echo IDT Image Gallery - Local Test Server
echo ========================================
echo.
echo Starting Python web server on port 8000...
echo.
echo The gallery will open in your browser automatically.
echo.
echo Press Ctrl+C to stop the server when done.
echo ========================================
echo.

REM Wait a moment for server to start, then open browser
start "" http://localhost:8000/index.html

REM Start the Python web server (this will block until Ctrl+C)
python -m http.server 8000

REM This line only runs after Ctrl+C
echo.
echo Server stopped.
pause
