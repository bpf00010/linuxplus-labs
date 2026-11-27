#!/usr/bin/env bash
set -euo pipefail

mkdir -p /usr/local/bin

# 1. Create cpu-hog script and service
cat <<'EOF' > /usr/local/bin/cpu-hog.sh
#!/usr/bin/env bash
while true; do
    sleep 2
done
EOF
chmod 0755 /usr/local/bin/cpu-hog.sh

cat <<'EOF' > /etc/systemd/system/cpu-hog.service
[Unit]
Description=CPU Hog Worker
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/cpu-hog.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 2. Create batch-job script and service with Nice=0
cat <<'EOF' > /usr/local/bin/batch-job.sh
#!/usr/bin/env bash
while true; do
    sleep 5
done
EOF
chmod 0755 /usr/local/bin/batch-job.sh

cat <<'EOF' > /etc/systemd/system/batch-job.service
[Unit]
Description=Batch Job Worker
After=network.target

[Service]
Type=simple
Nice=0
ExecStart=/usr/local/bin/batch-job.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 3. Create pre-installed heartbeat script
cat <<'EOF' > /usr/local/bin/heartbeat.sh
#!/usr/bin/env bash
date '+%Y-%m-%d %H:%M:%S ok' >> /var/tmp/heartbeat.log
EOF
chmod 0755 /usr/local/bin/heartbeat.sh

# 4. Create cronuser and leave /etc/cron.allow missing
id -u cronuser >/dev/null 2>&1 || useradd -m -s /bin/bash cronuser
rm -f /etc/cron.allow
crontab -r -u sysadmin >/dev/null 2>&1 || true

# 5. Start services and stop cron.service
systemctl daemon-reload >/dev/null 2>&1 || true
systemctl enable --now cpu-hog.service >/dev/null 2>&1 || true
systemctl enable --now batch-job.service >/dev/null 2>&1 || true
systemctl stop cron.service >/dev/null 2>&1 || true
