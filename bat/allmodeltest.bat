@echo off
REM Test all offline (Ollama) models on a specific directory
REM Usage: allmodeltest.bat
REM Processes: \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo ========================================
echo Testing ALL Ollama Models
echo ========================================
echo Target: \\ford\home\Photos\MobileBackup\iPhone\2018\09
echo.

echo.
echo [1/10] Running Ollama Moondream...
call run_ollama_moondream.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [2/10] Running Ollama LLaVA 7B...
call run_ollama_llava7b.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [3/10] Running Ollama LLaVA...
call run_ollama_llava.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [4/10] Running Ollama LLaVA Llama3...
call run_ollama_llava_llama3.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [5/10] Running Ollama LLaVA Phi3...
call run_ollama_llava_phi3.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [6/10] Running Ollama BakLLaVA...
call run_ollama_bakllava.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [7/10] Running Ollama Llama 3.2 Vision 11B...
call run_ollama_llama32vision11b.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [8/10] Running Ollama Llama 3.2 Vision...
call run_ollama_llama32vision.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [9/10] Running Ollama Mistral...
call run_ollama_mistral.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [10/10] Running Ollama Gemma...
call run_ollama_gemma.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo ========================================
echo All model tests complete!
echo ========================================
echo Results in: ..\Descriptions\wf_ollama_*
echo.
pause
