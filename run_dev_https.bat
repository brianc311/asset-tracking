@echo off
cd /d %~dp0
call .venv\Scripts\activate

pip install django-extensions Werkzeug pyOpenSSL -q

for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\.' } | Select-Object -First 1 -ExpandProperty IPAddress)"') do set LAPTOP_IP=%%i

echo.
echo Asset Tracking HTTPS dev server (camera works on phone)
echo.
echo   Laptop:      https://127.0.0.1:8443/
echo   Laptop:      https://localhost:8443/
if defined LAPTOP_IP (
  echo   Phone scan:  https://%LAPTOP_IP%:8443/scan/
  echo   Phone login: https://%LAPTOP_IP%:8443/login/
  echo.
  echo   First visit: tap Advanced - Proceed anyway (self-signed cert)
) else (
  echo   Could not detect Wi-Fi IP. Run: ipconfig
)
echo.

python manage.py runserver_plus 0.0.0.0:8443 --cert-file adhoc
