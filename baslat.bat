@echo off
rem OMS Montaj uygulamasini bu bilgisayarda baslatir. Ayrinti: oms_montaj\__main__.py
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Kurulum eksik. Once kurulum.bat dosyasini calistirin.
    pause
    exit /b 1
)
rem Yapay zeka asistani (sag alttaki sohbet kutusu): anahtar "OMS Veri\anthropic-anahtar.txt" dosyasindan okunur.
set "OMS_ANAHTAR_DOSYASI=%~dp0OMS Veri\anthropic-anahtar.txt"
set OMS_ASISTAN=1
".venv\Scripts\python.exe" -m oms_montaj
pause
