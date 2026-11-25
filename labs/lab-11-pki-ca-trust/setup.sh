#!/usr/bin/env bash
set -euo pipefail

# Create sysadmin user if not present
id -u sysadmin &>/dev/null || useradd -m -s /bin/bash sysadmin
echo "sysadmin:linuxplus" | chpasswd

# 1. Generate Internal Root CA
mkdir -p /etc/lab-ca
openssl genrsa -out /etc/lab-ca/ca.key 2048 2>/dev/null
openssl req -x509 -new -nodes -key /etc/lab-ca/ca.key \
    -sha256 -days 3650 -out /etc/lab-ca/ca.crt \
    -subj "/CN=Lab Internal Root CA/O=Lab Corp/C=US" 2>/dev/null

# 2. Configure /etc/hosts
if ! grep -q 'portal.lab.internal' /etc/hosts; then
    echo "127.0.0.1 portal.lab.internal" >> /etc/hosts
fi

# 3. Generate a BROKEN self-signed cert (wrong CN, no SAN, not signed by CA)
mkdir -p /etc/ssl/lab-portal
openssl genrsa -out /etc/ssl/lab-portal/portal.key 2048 2>/dev/null
openssl req -new -x509 -nodes -key /etc/ssl/lab-portal/portal.key \
    -sha256 -days 365 -out /etc/ssl/lab-portal/portal.crt \
    -subj "/CN=wrong.local/O=Unknown/C=US" 2>/dev/null
chmod 644 /etc/ssl/lab-portal/portal.key

# 4. Configure Nginx to serve on 127.0.0.1:18450 with the broken cert
cat > /etc/nginx/sites-available/portal-tls <<'NGINX'
server {
    listen 127.0.0.1:18450 ssl;
    server_name portal.lab.internal;

    ssl_certificate     /etc/ssl/lab-portal/portal.crt;
    ssl_certificate_key /etc/ssl/lab-portal/portal.key;

    location / {
        default_type application/json;
        return 200 '{"pki":"trusted"}';
    }
}
NGINX

ln -sf /etc/nginx/sites-available/portal-tls /etc/nginx/sites-enabled/portal-tls
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Reload nginx (may fail if systemd not ready, that's okay for setup)
systemctl daemon-reload 2>/dev/null || true
systemctl enable nginx.service 2>/dev/null || true
systemctl restart nginx.service 2>/dev/null || true
