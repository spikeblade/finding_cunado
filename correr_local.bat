@echo off
echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo Corriendo monitor...
python monitor_github.py

echo.
pause
