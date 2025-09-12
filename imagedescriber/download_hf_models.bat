@echo off
REM Hugging Face Model Downloader for Windows
REM Usage: download_hf_models.bat [model_name|all|list]

if "%1"=="" (
    echo Usage: download_hf_models.bat [model_name^|all^|list]
    echo.
    echo Examples:
    echo   download_hf_models.bat list
    echo   download_hf_models.bat blip2-opt
    echo   download_hf_models.bat all
    exit /b 1
)

if "%1"=="list" (
    python download_hf_models.py --list
) else if "%1"=="all" (
    python download_hf_models.py --all
) else (
    python download_hf_models.py --model %1
)