@echo off
chcp 65001 >nul
REM CRIMESIGHT Revival - lanzador (sin crear el .exe)
python -m pip install -q -r "%~dp0requirements.txt" || goto :error
start "" pythonw "%~dp0launcher\webapp.py"
exit /b 0
:error
echo Algo ha fallado instalando dependencias.
pause
exit /b 1
