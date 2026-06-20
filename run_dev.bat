@echo off
cd /d %~dp0
call .venv\Scripts\activate
echo.
echo Asset Tracking dev server
echo   Laptop:  http://127.0.0.1:8000
echo   Phone:   http://192.168.1.105:8000/scan/
echo.
python manage.py runserver 0.0.0.0:8000
