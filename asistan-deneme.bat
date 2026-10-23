@echo off
rem Yapay zeka asistanini UYDURMA veriyle dener: ayri bir veri klasoru (OMS Veri\asistan-deneme)
rem ve ayri bir adres (http://localhost:8091). Gercek veritabanina dokunmaz; asistan yalnizca
rem bu deneme verisini gorur. API anahtari "OMS Veri\anthropic-anahtar.txt" dosyasindan okunur.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Kurulum eksik. Once kurulum.bat dosyasini calistirin.
    pause
    exit /b 1
)
if not exist "OMS Veri\anthropic-anahtar.txt" (
    echo API anahtari yok. Anahtari "OMS Veri\anthropic-anahtar.txt" dosyasina tek satir olarak yazin.
    pause
    exit /b 1
)
set "OMS_ANAHTAR_DOSYASI=%~dp0OMS Veri\anthropic-anahtar.txt"
set "OMS_VERI_KLASORU=%~dp0OMS Veri\asistan-deneme"
set OMS_PORT=8091
set OMS_ASISTAN=1
".venv\Scripts\python.exe" araclar\asistan_deneme_verisi.py || goto hata
echo Deneme uygulamasi aciliyor; ilk acilista kendinize bir hesap olusturun.
".venv\Scripts\python.exe" -m oms_montaj
pause
exit /b 0
:hata
echo Deneme verisi hazirlanamadi. Yukaridaki hatayi Claude'a iletin.
pause
exit /b 1
