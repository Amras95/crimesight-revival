@echo off
chcp 65001 >nul
title CRIMESIGHT Revival - servidor
cd /d "%~dp0server"
python server.py --debug
pause
