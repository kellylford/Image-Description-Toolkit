@echo off
setlocal EnableExtensions

rem Source and destination
set "SRC=C:\idt\descriptions"
set "DST=\\qnap\home\idt\descriptions"

rem Log will be placed next to this script
set "LOG=%~dp0moveit.log"

rem Validate source exists
if not exist "%SRC%" (
  echo ERROR: Source not found: "%SRC%"
  pause
  exit /b 1
)

rem Ensure destination exists
if not exist "%DST%" (
  echo Creating destination: "%DST%"
  mkdir "%DST%" 2>nul
)

echo Starting copy without deletions (new and updated files only)
echo From: "%SRC%"
echo To  : "%DST%"
echo Monitoring for changes every 15 minutes. Close this window to stop.
echo Log : "%LOG%"
echo.

rem Robocopy options:
rem  /E      = copy subdirectories, including empty ones
rem  /XO     = exclude older source files (don't overwrite newer destination files)
rem  /COPY:DAT /DCOPY:T = copy data, attributes, timestamps; keep dir timestamps
rem  /R:1 /W:2 = retry once, wait 2 seconds between retries
rem  /FFT    = assume FAT time granularity (2 seconds) to play nice with cloud sync
rem  /Z      = restartable mode for large files
rem  /MON:1  = run again when at least 1 change is detected
rem  /MOT:15 = check for changes every 15 minutes
rem  /TEE    = output to console as well as log
rem  /LOG+   = append to log file

robocopy "%SRC%" "%DST%" *.* /E /XO /COPY:DAT /DCOPY:T /R:1 /W:2 /FFT /Z /MON:1 /MOT:15 /TEE /LOG+:"%LOG%"
set "RC=%ERRORLEVEL%"

rem Robocopy uses non-zero codes for normal situations; only 8 and above mean failure
if %RC% GEQ 8 goto :rc_fail

echo Robocopy finished. Exit code: %RC%
exit /b 0

:rc_fail
echo Robocopy reported failures. Exit code: %RC%
exit /b %RC%
