@echo off
cd /d %~dp0
call .venv\Scripts\activate

pip install django-extensions Werkzeug pyOpenSSL -q

REM Windows HTTP.sys often reserves 8443 (shows a generic 404). Use 8444.
set HTTPS_PORT=8444

for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\.' } | Select-Object -First 1 -ExpandProperty IPAddress)"') do set LAPTOP_IP=%%i

echo.
echo Asset Tracking HTTPS dev server (camera works on phone)
echo.
echo   Laptop:      https://127.0.0.1:%HTTPS_PORT%/
echo   Laptop:      https://localhost:%HTTPS_PORT%/
if defined LAPTOP_IP (
  echo   Phone scan:  https://%LAPTOP_IP%:%HTTPS_PORT%/scan/
  echo   Phone login: https://%LAPTOP_IP%:%HTTPS_PORT%/login/
  echo.
  echo   First visit: tap Advanced - Proceed anyway (self-signed cert)
) else (
  echo   Could not detect Wi-Fi IP. Run: ipconfig
)
echo.

python manage.py runserver_plus 0.0.0.0:%HTTPS_PORT% --cert-file adhoc
