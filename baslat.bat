@echo off
rem OMS Montaj uygulamasini bu bilgisayarda baslatir. Ayrinti: oms_montaj\__main__.py
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Kurulum eksik. Once kurulum.bat dosyasini calistirin.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m oms_montaj
pause
