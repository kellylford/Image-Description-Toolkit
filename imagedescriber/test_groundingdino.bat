@echo off
echo ================================================================
echo    ImageDescriber - GroundingDINO Installation Test
echo ================================================================
echo.
echo This script tests if GroundingDINO is properly installed and working.
echo.
pause

echo.
echo [1/5] Testing Python availability...
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ FAIL: Python not found
    echo   Solution: Install Python from https://www.python.org
    goto :test_failed
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo ✓ PASS: Python %%i found
)

echo.
echo [2/5] Testing GroundingDINO import...
python -c "import groundingdino" >nul 2>&1
if errorlevel 1 (
    echo ✗ FAIL: GroundingDINO not installed
    echo   Solution: Run install_groundingdino.bat
    goto :test_failed
) else (
    echo ✓ PASS: GroundingDINO package found
)

echo.
echo [3/5] Testing PyTorch...
python -c "import torch; print('✓ PASS: PyTorch', torch.__version__)"
if errorlevel 1 (
    echo ✗ FAIL: PyTorch not installed
    echo   Solution: pip install torch torchvision
    goto :test_failed
)

echo.
echo [4/5] Testing TorchVision...
python -c "import torchvision; print('✓ PASS: TorchVision', torchvision.__version__)"
if errorlevel 1 (
    echo ✗ FAIL: TorchVision not installed
    echo   Solution: pip install torchvision
    goto :test_failed
)

echo.
echo [5/5] Testing GroundingDINO functionality...
echo (This will check if the provider can be initialized)
python -c "from groundingdino.util.inference import Model; print('✓ PASS: GroundingDINO core components working')" >nul 2>&1
if errorlevel 1 (
    echo ✗ FAIL: GroundingDINO components not working
    echo   This might be a version compatibility issue
    echo   Try reinstalling: pip install --upgrade groundingdino-py torch torchvision
    goto :test_failed
) else (
    echo ✓ PASS: GroundingDINO core components working
)

echo.
echo ================================================================
echo ALL TESTS PASSED! ✓
echo ================================================================
echo.
echo GroundingDINO is properly installed and ready to use!
echo.
echo Important Notes:
echo.
echo 1. Model Download (First Use Only):
echo    - On first detection, ~700MB model downloads automatically
echo    - Takes 2-10 minutes depending on internet
echo    - After first download, works offline
echo    - Cache location: C:\Users\%USERNAME%\.cache\groundingdino\
echo.
echo 2. GPU Support:
python -c "import torch; print('   - GPU Available: ' + ('YES (Faster detection!)' if torch.cuda.is_available() else 'NO (CPU mode - works but slower)'))" 2>nul
if errorlevel 1 (
    echo    - GPU Status: Unknown
)
echo    - CPU mode works fine, just slower than GPU
echo.
echo 3. Usage in ImageDescriber:
echo    - Provider dropdown: Select "GroundingDINO" or "GroundingDINO + Ollama"
echo    - Detection mode: Automatic (presets) or Custom (your queries)
echo    - Confidence: Adjust threshold (default 25%%)
echo    - Chat mode: Type "find [objects]" for interactive detection
echo.
echo 4. Example Queries:
echo    "red cars . blue trucks"
echo    "people wearing safety helmets"
echo    "fire exits . emergency signs"
echo    "damaged equipment . missing parts"
echo.
echo You're all set! Start using GroundingDINO in ImageDescriber.
echo.
goto :end

:test_failed
echo.
echo ================================================================
echo TESTS FAILED ✗
echo ================================================================
echo.
echo Some components are not properly installed.
echo Please review the errors above and:
echo   1. Run install_groundingdino.bat to install/fix
echo   2. Check for error messages during installation
echo   3. See troubleshooting section below
echo.
echo Common Issues:
echo.
echo • Python not found:
echo   - Install from https://www.python.org
echo   - Ensure "Add to PATH" was checked during install
echo   - Restart Command Prompt after installation
echo.
echo • pip not working:
echo   - Run: python -m pip install --upgrade pip
echo   - Try running Command Prompt as Administrator
echo.
echo • GroundingDINO not found:
echo   - Run: install_groundingdino.bat
echo   - Or manually: pip install groundingdino-py torch torchvision
echo.
echo • Import errors:
echo   - Missing Visual C++ Build Tools (Windows)
echo   - Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
echo   - Install "Desktop development with C++" workload
echo.
echo • Version conflicts:
echo   - Try: pip install --upgrade groundingdino-py torch torchvision
echo   - Or fresh install: pip uninstall groundingdino-py torch torchvision
echo                       pip install groundingdino-py torch torchvision
echo.

:end
pause
