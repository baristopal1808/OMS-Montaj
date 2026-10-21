@echo off
rem Uygulamanin kutuphanelerini projeye ozel klasore (.venv) kurar. Bir kez calistirilir;
rem requirements.txt degisince yeniden calistirilir.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv || goto hata
".venv\Scripts\python.exe" -m pip install --upgrade pip || goto hata
".venv\Scripts\python.exe" -m pip install -r requirements-gelistirme.txt || goto hata
echo Kurulum tamam. Uygulamayi baslat.bat ile acabilirsiniz.
pause
exit /b 0
:hata
echo Kurulum basarisiz oldu. Yukaridaki hatayi Claude'a iletin.
pause
exit /b 1
