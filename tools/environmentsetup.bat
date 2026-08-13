@echo off
REM ============================================================================
REM Environment Setup - delegates to winsetup.bat
REM ============================================================================
REM This script is the entry point tools\bootstrap.bat calls after cloning the
REM repository. It does not set anything up itself; winsetup.bat at the project
REM root is the single implementation.
REM
REM WHY THIS IS A SHIM (2026-08-13)
REM
REM The previous version was a full second implementation that had rotted past
REM the point of working at all:
REM
REM   - "cd viewer" and "cd idtconfigure" -- both directories were removed when
REM     Viewer, PromptEditor and Configure were folded into ImageDescriber. cmd
REM     does not stop on a failed cd, so the script carried on in whatever
REM     directory it happened to be in and the following "cd .." walked ABOVE
REM     the project root. Everything after that ran in the wrong place.
REM   - It created .venv on Windows. The convention is .winenv, precisely so a
REM     macOS .venv and a Windows .winenv can coexist in one checkout. Nothing
REM     in the build system looks for a Windows .venv, so even the parts that
REM     succeeded produced environments no build script would ever find.
REM   - Step numbering read [1/4], [2/3], [3/3], [5/5].
REM   - It pointed at releaseitall.bat, which does not exist.
REM   - It never knew about IDT Chat.
REM
REM Because bootstrap.bat calls this file, that was the documented path for a
REM brand-new contributor. Delegating removes the duplicate rather than
REM repairing it: two setup scripts is how this one drifted while nobody was
REM running it.
REM ============================================================================

REM Project root, one level up from tools\
cd /d "%~dp0.."

if not exist "winsetup.bat" (
    echo ERROR: winsetup.bat not found at the project root: %CD%
    echo The repository may be incomplete or corrupt.
    exit /b 1
)

call winsetup.bat
exit /b %ERRORLEVEL%
