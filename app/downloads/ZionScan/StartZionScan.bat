@echo off
setlocal
cd /d "%~dp0"
start "" "%~dp0ZkFingerAgent.exe"
%timeout /t 1 /nobreak > nul
start "" "%~dp0ZionScan.exe"
