@echo off
REM Remove Claude (Anthropic) API key environment variable
REM Usage: remove_claude_key.bat
REM
REM This removes ANTHROPIC_API_KEY from the current session only.

set ANTHROPIC_API_KEY=

echo ANTHROPIC_API_KEY environment variable has been removed from this session.
