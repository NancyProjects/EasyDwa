@echo off
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 (echo Install Python 3.12 or newer from python.org, then try again.& pause & exit /b 1)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (pause & exit /b 1)
.venv\Scripts\python.exe manage.py migrate
if errorlevel 1 (pause & exit /b 1)
echo Create your administrator username and password:
.venv\Scripts\python.exe manage.py createsuperuser
pause
