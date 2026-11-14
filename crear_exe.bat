@echo off
chcp 65001 >nul
REM CRIMESIGHT Revival - crea dist\CrimeSightRevival.exe (version de desarrollo, no se actualiza sola)
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller || goto :error
python tools\build_exe.py || goto :error
pause
exit /b 0
:error
echo.
echo Algo ha fallado. Revisa el mensaje de arriba.
pause
exit /b 1
