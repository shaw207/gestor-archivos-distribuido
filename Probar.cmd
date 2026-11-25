@echo off
setlocal
wsl.exe -d Ubuntu --cd "%~dp0." -- sh ./demo.sh %*
set "result=%errorlevel%"
if "%~1"=="" pause
exit /b %result%
