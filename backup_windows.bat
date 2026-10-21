@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Run setup_windows.bat first.& pause & exit /b 1)
if not exist shop.sqlite3 (echo No database yet.& pause & exit /b 1)
if not exist backups mkdir backups
.venv\Scripts\python.exe -c "import sqlite3,datetime,pathlib; p=pathlib.Path('backups')/('shop-'+datetime.datetime.now().strftime('%%Y%%m%%d-%%H%%M%%S')+'.sqlite3'); src=sqlite3.connect('shop.sqlite3'); dst=sqlite3.connect(str(p)); src.backup(dst); dst.close(); src.close(); print('Backup saved:',p)"
pause
