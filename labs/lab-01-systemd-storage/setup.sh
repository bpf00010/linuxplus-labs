#!/usr/bin/env bash
set -euo pipefail

# 1. Create loopback backing file and ext4 filesystem
mkdir -p /var/lib/lplab /mnt/appdata
dd if=/dev/zero of=/var/lib/lplab/appdata.img bs=1M count=64 status=none
mkfs.ext4 -F /var/lib/lplab/appdata.img >/dev/null 2>&1

# 2. Plant broken /etc/fstab entry referencing nonexistent image file
touch /etc/fstab
sed -i '/\/mnt\/appdata/d' /etc/fstab
echo "/var/lib/lplab/appdata_missing.img /mnt/appdata ext4 loop,defaults 0 0" >> /etc/fstab

# 3. Create worker binary
mkdir -p /usr/local/bin
cat <<'EOF' > /usr/local/bin/app-worker
#!/usr/bin/env bash
echo "app-worker starting up..."
while true; do
    sleep 3
done
EOF
chmod 755 /usr/local/bin/app-worker

# 4. Create systemd unit with invalid ExecStart path, reload, and mask
cat <<'EOF' > /etc/systemd/system/app-worker.service
[Unit]
Description=Application Background Worker
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/app-worker-corrupted
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload >/dev/null 2>&1 || true
systemctl mask app-worker.service >/dev/null 2>&1 || true

# 5. Seed excessive unrotated log file
mkdir -p /var/log/app-worker
dd if=/dev/zero of=/var/log/app-worker/debug.log bs=1M count=25 status=none
rm -f /etc/logrotate.d/app-worker
