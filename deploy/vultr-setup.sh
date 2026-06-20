#!/bin/bash
# Asset Tracking — Vultr VPS deployment helper
# Run on your Vultr VPS after cloning from GitHub

set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/asset-tracking}"
DOMAIN="${DOMAIN:-yourdomain.com}"
REPO_URL="${REPO_URL:-git@github.com:brianc311/asset-tracking.git}"

echo "==> Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib certbot python3-certbot-nginx git

echo "==> Setting up PostgreSQL..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='asset_user'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER asset_user WITH PASSWORD 'CHANGE_ME_STRONG_PASSWORD';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='asset_tracking'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE asset_tracking OWNER asset_user;"

echo "==> Cloning or updating app..."
if [ ! -d "$APP_DIR" ]; then
  sudo mkdir -p "$APP_DIR"
  sudo chown "$USER:$USER" "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"
git pull origin main

echo "==> Python virtualenv..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "!! Edit $APP_DIR/.env with production values before continuing !!"
fi

echo "==> Django setup..."
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py setup_site --username admin --password 'CHANGE_ME'

echo "==> Gunicorn systemd service..."
sudo tee /etc/systemd/system/asset-tracking.service > /dev/null <<EOF
[Unit]
Description=Asset Tracking Gunicorn
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/nginx/sites-available/asset-tracking > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 20M;

    location /static/ {
        alias $APP_DIR/staticfiles/;
    }
    location /media/ {
        alias $APP_DIR/media/;
    }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/asset-tracking /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable asset-tracking
sudo systemctl restart asset-tracking
sudo systemctl restart nginx

echo "==> HTTPS with Let's Encrypt..."
echo "Run: sudo certbot --nginx -d $DOMAIN"
echo "Then set in .env: DEBUG=False, SECURE_SSL_REDIRECT=True, CSRF_TRUSTED_ORIGINS=https://$DOMAIN"
echo "Done! Visit http://$DOMAIN"
