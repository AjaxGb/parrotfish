@echo off
cd %~dp0
title Parrotfish
:begin
python -m parrotfish
echo Stopped! Press any key to restart...
pause >nul
echo Restarting...
goto begin