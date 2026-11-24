#!/usr/bin/env bash
set -euo pipefail

# 1. Install metrics-collector executable
mkdir -p /usr/local/bin /var/log
cat <<'EOF' > /usr/local/bin/metrics-collector.sh
#!/usr/bin/env bash
echo "metrics-collector initialized" >> /var/log/metrics-collector.log
while true; do
    date '+%Y-%m-%d %H:%M:%S metrics ok' >> /var/log/metrics-collector.log
    sleep 5
done
EOF
chmod 755 /usr/local/bin/metrics-collector.sh

# 2. Install metrics-collector systemd service
cat <<'EOF' > /etc/systemd/system/metrics-collector.service
[Unit]
Description=Metrics Collector Agent
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/metrics-collector.sh
Restart=no

[Install]
WantedBy=multi-user.target
EOF

# 3. Leave metrics-collector stopped and disabled
systemctl daemon-reload >/dev/null 2>&1 || true
systemctl stop metrics-collector.service >/dev/null 2>&1 || true
systemctl disable metrics-collector.service >/dev/null 2>&1 || true

# 4. Drop broken legacy cron job
mkdir -p /etc/cron.d
cat <<'EOF' > /etc/cron.d/metrics-watchdog
* * * * * root /usr/local/bin/nonexistent-watchdog.sh >/dev/null 2>&1
EOF
chmod 644 /etc/cron.d/metrics-watchdog

# Ensure any previous watchdog units are cleaned
systemctl stop metrics-watchdog.timer >/dev/null 2>&1 || true
systemctl disable metrics-watchdog.timer >/dev/null 2>&1 || true
rm -f /etc/systemd/system/metrics-watchdog.service /etc/systemd/system/metrics-watchdog.timer /usr/local/bin/metrics-watchdog.sh
systemctl daemon-reload >/dev/null 2>&1 || true
