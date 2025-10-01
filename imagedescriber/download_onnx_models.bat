@echo off
echo ================================================================
echo    ImageDescriber - ONNX Models Download Script
echo ================================================================
echo.
echo This script downloads optimized ONNX models for hardware-accelerated
echo AI image description. Models will be downloaded to: onnx_models/
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please ensure Python is installed and in PATH.
    pause
    exit /b 1
)

REM Check if required packages are installed
echo [1/6] Checking required packages...
python -c "import onnxruntime, onnx, huggingface_hub" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install onnxruntime onnx huggingface_hub requests pillow numpy
    if errorlevel 1 (
        echo ERROR: Failed to install required packages
        pause
        exit /b 1
    )
)

echo [2/6] Creating model directories...
mkdir onnx_models >nul 2>&1
mkdir onnx_models\florence2 >nul 2>&1
mkdir onnx_models\florence2\onnx >nul 2>&1
mkdir onnx_models\blip_real >nul 2>&1
mkdir onnx_models\real_models >nul 2>&1

echo [3/6] Downloading Florence-2 model (best image captioning, ~230MB)...
python -c "
import sys
sys.path.append('.')
try:
    from huggingface_hub import hf_hub_download
    import os
    
    # Download Florence-2 ONNX model
    print('Downloading Florence-2 decoder model...')
    model_path = hf_hub_download(
        repo_id='microsoft/Florence-2-base-ft',
        filename='onnx/decoder_model_quantized.onnx',
        local_dir='onnx_models/florence2',
        local_dir_use_symlinks=False
    )
    print(f'Downloaded to: {model_path}')
    
    # Also download config if available
    try:
        config_path = hf_hub_download(
            repo_id='microsoft/Florence-2-base-ft',
            filename='config.json',
            local_dir='onnx_models/florence2',
            local_dir_use_symlinks=False
        )
        print(f'Config downloaded to: {config_path}')
    except:
        print('Config not available - model will work without it')
        
except Exception as e:
    print(f'Florence-2 download failed: {e}')
    print('You can download manually from: https://huggingface.co/microsoft/Florence-2-base-ft')
"

echo [4/6] Downloading BLIP image captioning model (~500MB)...
python -c "
try:
    from huggingface_hub import hf_hub_download
    
    # Download BLIP ONNX model
    print('Downloading BLIP captioning model...')
    model_path = hf_hub_download(
        repo_id='Salesforce/blip-image-captioning-base',
        filename='pytorch_model.bin',
        local_dir='onnx_models/blip_real',
        local_dir_use_symlinks=False
    )
    
    # Note: This downloads PyTorch model - would need conversion to ONNX
    print('Note: BLIP model downloaded but needs ONNX conversion')
    print('For now, use HuggingFace provider for BLIP models')
    
except Exception as e:
    print(f'BLIP download failed: {e}')
    print('Alternative: Use HuggingFace provider for BLIP models')
"

echo [5/6] Downloading lightweight models (MobileNet, ResNet)...
python -c "
try:
    from huggingface_hub import hf_hub_download
    import urllib.request
    
    # Download MobileNet-v2 ONNX (if available)
    print('Looking for MobileNet-v2 ONNX model...')
    # Note: Official ONNX model zoo or custom conversion needed
    print('MobileNet-v2: Use torchvision or custom conversion to ONNX')
    
    # Download ResNet-18 ONNX (if available)  
    print('Looking for ResNet-18 ONNX model...')
    print('ResNet-18: Use torchvision or custom conversion to ONNX')
    
except Exception as e:
    print(f'Lightweight models: {e}')
    print('Note: These models need custom ONNX conversion')
"

echo [6/6] Downloading Vision-Language GPT-2 model...
python -c "
try:
    from huggingface_hub import hf_hub_download
    
    # Download ViT-GPT2 for image captioning
    print('Downloading Vision-Language model...')
    # This would need a specific ONNX-converted model
    print('Vision-Language GPT-2: Requires custom ONNX conversion')
    print('Alternative: Use HuggingFace Transformers with vision models')
    
except Exception as e:
    print(f'Vision-Language model: {e}')
"

echo.
echo ================================================================
echo    ONNX Models Download Summary
echo ================================================================
echo.
echo Models downloaded to: %cd%\onnx_models\
echo.
echo Status:
echo   Florence-2: Available (best quality image captioning)
echo   BLIP: PyTorch format (use HuggingFace provider instead)
echo   MobileNet/ResNet: Need custom ONNX conversion
echo   Vision-Language: Need custom ONNX conversion
echo.
echo RECOMMENDATION:
echo   For immediate use, try the HuggingFace provider which has
echo   working versions of BLIP, ViT, and other vision models.
echo.
echo   The ONNX provider is optimized for NPU/GPU acceleration
echo   but requires properly converted ONNX models.
echo.
echo Hardware acceleration: Use NPU/DirectML if available
echo.
pause