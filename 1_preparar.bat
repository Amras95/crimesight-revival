@echo off
chcp 65001 >nul
REM CRIMESIGHT Revival - preparacion (solo la primera vez)
set GAME=D:\SteamLibrary\steamapps\common\CrimeSight
python -m pip install -r "%~dp0requirements.txt" || goto :error
python "%~dp0tools\extract_keys.py" "%GAME%" || goto :error
python "%~dp0tools\patch_client.py" "%GAME%" || goto :error
python "%~dp0tools\credits_patch.py" "%GAME%" || goto :error
echo.
echo Listo. Ahora abre 2_servidor.bat y despues lanza el juego desde Steam.
pause
exit /b 0
:error
echo.
echo Algo ha fallado. Revisa el mensaje de arriba.
pause
exit /b 1
