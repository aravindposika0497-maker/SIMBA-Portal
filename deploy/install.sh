#!/usr/bin/env bash
# Install or update the SIMBA portal on Ubuntu 24.04.
# Run from the unpacked project directory:   sudo bash deploy/install.sh
# Safe to re-run: it updates code and dependencies but never overwrites an existing env file.
set -euo pipefail

APP_DIR=/opt/simba-portal
ENV_DIR=/etc/simba-portal
ENV_FILE="$ENV_DIR/simba-portal.env"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo bash deploy/install.sh" >&2
  exit 1
fi

echo "==> Installing OS packages"
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip nginx rsync curl

echo "==> Creating service user"
id simba >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /var/lib/simba-portal --shell /usr/sbin/nologin simba

echo "==> Copying application to $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a --delete --exclude venv --exclude .env --exclude '__pycache__' --exclude '.pytest_cache' "$SRC_DIR/" "$APP_DIR/"

echo "==> Creating virtual environment and installing dependencies"
[[ -d "$APP_DIR/venv" ]] || python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip wheel
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> Environment file"
mkdir -p "$ENV_DIR"
if [[ ! -f "$ENV_FILE" ]]; then
  cp "$APP_DIR/.env.example" "$ENV_FILE"
  echo "    Created $ENV_FILE from .env.example (demo mode, auth disabled). Edit it before go-live."
else
  echo "    Keeping existing $ENV_FILE"
fi
chown root:simba "$ENV_DIR" "$ENV_FILE"
chmod 750 "$ENV_DIR"
chmod 640 "$ENV_FILE"

echo "==> Permissions (code is read-only to the service user)"
chown -R root:simba "$APP_DIR"
find "$APP_DIR" -path "$APP_DIR/venv" -prune -o -type d -exec chmod 750 {} +
find "$APP_DIR" -path "$APP_DIR/venv" -prune -o -type f -exec chmod 640 {} +
chmod -R g+rX,o-rwx "$APP_DIR/venv"
# Nginx (www-data) serves /static directly
chmod 755 "$APP_DIR"
find "$APP_DIR/static" -type d -exec chmod 755 {} +
find "$APP_DIR/static" -type f -exec chmod 644 {} +

echo "==> systemd service"
install -m 644 "$APP_DIR/deploy/simba-portal.service" /etc/systemd/system/simba-portal.service
systemctl daemon-reload
systemctl enable simba-portal
systemctl restart simba-portal

echo "==> Nginx"
install -m 644 "$APP_DIR/deploy/nginx-simba-portal.conf" /etc/nginx/sites-available/simba-portal
ln -sf /etc/nginx/sites-available/simba-portal /etc/nginx/sites-enabled/simba-portal
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl reload nginx || systemctl restart nginx

echo "==> Smoke test"
for i in $(seq 1 20); do
  if curl -fsS http://127.0.0.1/api/health >/dev/null 2>&1; then
    echo "    /api/health OK"
    curl -fsS http://127.0.0.1/api/health; echo
    echo "Done. Check status with: systemctl status simba-portal ; journalctl -u simba-portal -n 100"
    exit 0
  fi
  sleep 1
done
echo "Health check FAILED. Recent logs:" >&2
journalctl -u simba-portal -n 60 --no-pager >&2 || true
exit 1
