#!/usr/bin/env bash
set -euo pipefail

# 1. Configure Nginx site with deliberate syntax error (missing semicolon on listen directive)
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
cat <<'EOF' > /etc/nginx/sites-available/internal-api
server {
    listen 127.0.0.1:18080
    server_name api.lab.internal;

    location /health {
        default_type application/json;
        return 200 '{"status":"healthy","service":"internal-api"}\n';
    }
}
EOF

ln -sf /etc/nginx/sites-available/internal-api /etc/nginx/sites-enabled/internal-api
rm -f /etc/nginx/sites-enabled/default

# Stop nginx until student resolves syntax
systemctl stop nginx >/dev/null 2>&1 || true

# 2. Add faulty /etc/hosts mapping
sed -i '/api\.lab\.internal/d' /etc/hosts
echo "127.0.0.99 api.lab.internal" >> /etc/hosts

# 3. Create strictly scoped nftables table dropping port 18080
# Safety rule: NEVER touch other tables in WSL2 shared netns
nft delete table inet lplab02 >/dev/null 2>&1 || true
nft add table inet lplab02
nft 'add chain inet lplab02 input { type filter hook input priority 0; policy accept; }'
nft add rule inet lplab02 input tcp dport 18080 drop
