# Asset Tracking

White-label asset tracking platform with barcode/QR scanning, admin console, status page, and role-based access.

## Features

- **Asset management** — product name, serial, model, location, comments, photos
- **Barcodes** — QR, Code 128, Code 39, EAN-13 generation and printing
- **Mobile scan page** — camera barcode scanner, session running totals, print + PDF export
- **White-label branding** — logo, colors, headers, footers, page titles from admin console
- **Status page** — public health dashboard with incident/outage management
- **Roles** — Super User, Admin, Staff, User
- **reCAPTCHA v2 checkbox** — on app login, scan login, and `/admin/` login
- **Light / dark mode** — per-user theme preference
- **Custom modals** — no browser alert/confirm dialogs

## Local Development

```powershell
cd Asset
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py setup_site
python manage.py runserver 0.0.0.0:8000
```

Open http://127.0.0.1:8000 on your laptop, or http://YOUR-LAPTOP-IP:8000/scan/ from your phone (same Wi‑Fi).

**Important:** Use `runserver 0.0.0.0:8000` (not plain `runserver`) so your phone can connect. On Windows you can double-click `run_dev.bat` instead.

### reCAPTCHA keys

1. Create keys at https://www.google.com/recaptcha/admin (reCAPTCHA v2 → "I'm not a robot" Checkbox)
2. Add to `.env`:
   ```
   RECAPTCHA_PUBLIC_KEY=your-site-key
   RECAPTCHA_PRIVATE_KEY=your-secret-key
   ```
3. For local testing, Google provides test keys (always pass):
   ```
   RECAPTCHA_PUBLIC_KEY=6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
   RECAPTCHA_PRIVATE_KEY=6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe
   ```

## URLs

| Path | Description |
|------|-------------|
| `/login/` | App login (reCAPTCHA) |
| `/admin/` | Django admin (reCAPTCHA) |
| `/assets/` | Asset list and management |
| `/scan/` | Mobile barcode scanner |
| `/status/` | Public status page |
| `/status/manage/` | Incident management (Admin+) |
| `/console/` | White-label branding (Super User) |

## GitHub Workflow

```powershell
git add .
git commit -m "Your message"
git push origin main
```

## Vultr VPS Deployment

1. SSH into your Vultr VPS
2. Clone the repo:
   ```bash
   git clone git@github.com:brianc311/asset-tracking.git /var/www/asset-tracking
   ```
3. Run the setup script:
   ```bash
   cd /var/www/asset-tracking
   chmod +x deploy/vultr-setup.sh
   ./deploy/vultr-setup.sh
   ```
4. Edit `/var/www/asset-tracking/.env` for production:
   ```
   DEBUG=False
   USE_POSTGRES=True
   DB_NAME=asset_tracking
   DB_USER=asset_user
   DB_PASSWORD=your-strong-password
   DB_HOST=localhost
   ALLOWED_HOSTS=yourdomain.com,your-vultr-ip
   CSRF_TRUSTED_ORIGINS=https://yourdomain.com
   SECURE_SSL_REDIRECT=True
   SECRET_KEY=generate-a-long-random-string
   RECAPTCHA_PUBLIC_KEY=your-production-site-key
   RECAPTCHA_PRIVATE_KEY=your-production-secret-key
   ```
5. Enable HTTPS:
   ```bash
   sudo certbot --nginx -d yourdomain.com
   sudo systemctl restart asset-tracking
   ```

### Updating production

```bash
cd /var/www/asset-tracking
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart asset-tracking
```

## User Roles

| Role | Permissions |
|------|-------------|
| Super User | Everything + branding console + user management |
| Admin | Assets, status incidents, delete assets |
| Staff | Create/edit assets, scan, print reports |
| User | View assets (read-only) |

Assign roles in `/admin/` under Users.

## Tech Stack

- Python 3.11+ / Django 5
- PostgreSQL (production) / SQLite (local)
- Gunicorn + Nginx + Let's Encrypt
- ReportLab (PDF), python-barcode, qrcode, html5-qrcode
