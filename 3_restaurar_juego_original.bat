@echo off
chcp 65001 >nul
set GAME=D:\SteamLibrary\steamapps\common\CrimeSight
python "%~dp0tools\patch_client.py" "%GAME%" --restore
python "%~dp0tools\credits_patch.py" "%GAME%" --restore
pause
