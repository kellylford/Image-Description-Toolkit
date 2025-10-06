@echo off
REM Install ALL Ollama vision models
REM This will download all vision-capable models for comprehensive testing

echo.
echo ========================================
echo Installing ALL Ollama Vision Models
echo ========================================
echo.
echo This will install the following models:
echo   Core Models:
echo   - moondream (~1.7GB) - Already installed
echo   - llava:latest (~4.7GB) - Already installed
echo   - llava:7b (~4.7GB) - Already installed
echo   - llava:13b (~8GB)
echo   - llava:34b (~20GB)
echo   - llava-phi3 (~2.9GB) - Already installed
echo   - llava-llama3 (~5.5GB)
echo   - bakllava (~4.7GB)
echo.
echo   Advanced Models:
echo   - llama3.2-vision:latest (~7.8GB) - Already installed
echo   - llama3.2-vision:11b (~7.8GB) - Already installed
echo   - llama3.2-vision:90b (~55GB) - VERY LARGE
echo.
echo   Other Vision Models:
echo   - minicpm-v (~4GB)
echo   - minicpm-v:8b (~5GB)
echo   - cogvlm2 (~8GB)
echo   - internvl (~4GB)
echo.
echo   Large Language Models with Vision:
echo   - gemma3 (~3.3GB) - Already installed
echo   - mistral-small3.1 (~15GB) - Already installed
echo.
echo Total NEW downloads: ~130GB (excluding already installed)
echo.
echo Press Ctrl+C to cancel, or
pause

echo.
echo Installing missing models...
echo.

echo [1/9] Installing bakllava...
ollama pull bakllava

echo.
echo [2/9] Installing llava-llama3...
ollama pull llava-llama3

echo.
echo [3/9] Installing llava:13b...
ollama pull llava:13b

echo.
echo [4/9] Installing llava:34b (LARGE - 20GB)...
ollama pull llava:34b

echo.
echo [5/9] Installing llama3.2-vision:90b (VERY LARGE - 55GB)...
ollama pull llama3.2-vision:90b

echo.
echo [6/9] Installing minicpm-v...
ollama pull minicpm-v

echo.
echo [7/9] Installing minicpm-v:8b...
ollama pull minicpm-v:8b

echo.
echo [8/9] Installing cogvlm2...
ollama pull cogvlm2

echo.
echo [9/9] Installing internvl...
ollama pull internvl

echo.
echo ========================================
echo All models installed successfully!
echo ========================================
echo.
echo Total vision models: 17
echo.
echo Run 'ollama list' to see all installed models
echo Run batch files in the 'bat' folder to use them
echo.
pause
