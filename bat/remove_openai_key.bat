@echo off
REM Remove OpenAI API key environment variable
REM Usage: remove_openai_key.bat

cd /d "%~dp0\.."
REM
REM This removes OPENAI_API_KEY from the current session only.
set OPENAI_API_KEY=
echo OPENAI_API_KEY environment variable has been removed from this session.
