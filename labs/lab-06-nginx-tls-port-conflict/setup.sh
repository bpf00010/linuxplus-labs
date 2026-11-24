#!/usr/bin/env bash
set -euo pipefail

# 1. Create real backend service on 127.0.0.1:18445
cat <<'EOF' > /etc/systemd/system/portal-backend.service
[Unit]
Description=Portal Backend Internal Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -c "import http.server, socketserver; \
class H(http.server.BaseHTTPRequestHandler): \
    def do_GET(self): \
        self.send_response(200); \
        self.send_header('Content-Type','application/json'); \
        self.end_headers(); \
        self.wfile.write(b'{\"status\":\"healthy\",\"service\":\"portal-backend\"}\n'); \
    def log_message(self, *a): pass; \
socketserver.TCPServer(('127.0.0.1', 18445), H).serve_forever()"
Restart=always
User=nobody

[Install]
WantedBy=multi-user.target
EOF

# 2. Create rogue service squatting on 127.0.0.1:18443
cat <<'EOF' > /etc/systemd/system/legacy-stub.service
[Unit]
Description=Legacy Stub Listener
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -c "import socket; s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(('127.0.0.1', 18443)); s.listen(5); \
while True: \
    try: c, _ = s.accept(); c.close() \
    except: pass"
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 3. Generate self-signed TLS cert and insecure key
mkdir -p /etc/ssl/portal
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/portal/portal.key \
    -out /etc/ssl/portal/portal.crt \
    -subj "/C=US/ST=Lab/L=Lab/O=LinuxPlus/CN=localhost" >/dev/null 2>&1

chown nobody:nogroup /etc/ssl/portal/portal.key
chmod 0644 /etc/ssl/portal/portal.key

# 4. Create broken Nginx configuration
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
cat <<'EOF' > /etc/nginx/sites-available/portal-tls
server {
    listen 127.0.0.1:18443 ssl;
    server_name localhost;

    ssl_certificate /etc/ssl/portal/portal.crt;
    ssl_certificate_key /etc/ssl/portal/portal-missing.key;

    location / {
        proxy_pass http://127.0.0.1:18444;
        proxy_set_header Host $host;
    }
}
EOF

ln -sf /etc/nginx/sites-available/portal-tls /etc/nginx/sites-enabled/portal-tls
rm -f /etc/nginx/sites-enabled/default

# Stop nginx and start conflicting services
systemctl daemon-reload >/dev/null 2>&1 || true
systemctl stop nginx >/dev/null 2>&1 || true
systemctl enable --now portal-backend.service >/dev/null 2>&1 || true
systemctl enable --now legacy-stub.service >/dev/null 2>&1 || true
