@echo off
REM Test all offline (Ollama) models on a specific directory
REM Usage: allmodeltest.bat
REM Processes: \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo ========================================
echo Testing ALL 17 Ollama Vision Models
echo ========================================
echo Target: \\ford\home\Photos\MobileBackup\iPhone\2018\09
echo.

echo.
echo [1/17] Running Ollama Moondream...
call run_ollama_moondream.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [2/17] Running Ollama LLaVA 7B...
call run_ollama_llava7b.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [3/17] Running Ollama LLaVA...
call run_ollama_llava.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [4/17] Running Ollama LLaVA 13B...
call run_ollama_llava13b.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [5/17] Running Ollama LLaVA 34B...
call run_ollama_llava34b.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [6/17] Running Ollama LLaVA Phi3...
call run_ollama_llava_phi3.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [7/17] Running Ollama LLaVA Llama3...
call run_ollama_llava_llama3.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [8/17] Running Ollama BakLLaVA...
call run_ollama_bakllava.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [9/17] Running Ollama Llama 3.2 Vision...
call run_ollama_llama32vision.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [10/17] Running Ollama Llama 3.2 Vision 11B...
call run_ollama_llama32vision11b.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [11/17] Running Ollama Llama 3.2 Vision 90B...
call run_ollama_llama32vision90b.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [12/17] Running Ollama Mistral...
call run_ollama_mistral.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [13/17] Running Ollama Gemma...
call run_ollama_gemma.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [14/17] Running Ollama MiniCPM-V...
call run_ollama_minicpmv.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [15/17] Running Ollama MiniCPM-V 8B...
call run_ollama_minicpmv8b.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [16/17] Running Ollama CogVLM2...
call run_ollama_cogvlm2.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo [17/17] Running Ollama InternVL...
call run_ollama_internvl.bat \\ford\home\Photos\MobileBackup\iPhone\2018\09

echo.
echo ========================================
echo All 17 model tests complete!
echo ========================================
echo Results in: ..\Descriptions\wf_ollama_*
echo.
pause
