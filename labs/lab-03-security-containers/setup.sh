#!/usr/bin/env bash
set -euo pipefail

# 1. Create collaboration group and user accounts
getent group webops >/dev/null 2>&1 || groupadd webops
id -u deploy >/dev/null 2>&1 || useradd -m -s /bin/bash -g webops deploy
id -u auditor >/dev/null 2>&1 || useradd -m -s /bin/bash auditor

# 2. Seed misconfigured directory (owned by root:root, mode 0700, no setgid, no ACLs)
mkdir -p /srv/shared-app
chown root:root /srv/shared-app
chmod 0700 /srv/shared-app
setfacl -b /srv/shared-app >/dev/null 2>&1 || true

# 3. Create dummy service app-proxy
cat <<'EOF' > /etc/systemd/system/app-proxy.service
[Unit]
Description=App Proxy Gateway Service
After=network.target

[Service]
Type=simple
ExecStart=/bin/sleep infinity
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload >/dev/null 2>&1 || true

# 4. Plant overly permissive sudoers entry
mkdir -p /etc/sudoers.d
cat <<'EOF' > /etc/sudoers.d/99-deploy
# SECURITY VIOLATION: Excessive privileges
deploy ALL=(ALL) NOPASSWD: ALL
EOF
chmod 0440 /etc/sudoers.d/99-deploy
