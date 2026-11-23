#!/usr/bin/env bash
set -euo pipefail

# 1. Create metrics collector executable and systemd service
mkdir -p /usr/local/bin
cat <<'EOF' > /usr/local/bin/metrics-collector.sh
#!/usr/bin/env bash
echo "Metrics collector started at $(date)"
while true; do
    sleep 3
done
EOF
chmod 755 /usr/local/bin/metrics-collector.sh

cat <<'EOF' > /etc/systemd/system/metrics-collector.service
[Unit]
Description=Metrics Collector Daemon
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/metrics-collector.sh
Restart=no

[Install]
WantedBy=multi-user.target
EOF

# 2. Plant broken legacy cron entry
mkdir -p /etc/cron.d
echo "* * * * * root /usr/local/bin/nonexistent-watchdog.sh >/dev/null 2>&1" > /etc/cron.d/metrics-collector-watchdog

# 3. Clean any existing watchdog units & stop collector to simulate failure
rm -f /usr/local/bin/metrics-watchdog.sh
rm -f /etc/systemd/system/metrics-watchdog.service
rm -f /etc/systemd/system/metrics-watchdog.timer

systemctl daemon-reload >/dev/null 2>&1 || true
systemctl stop metrics-collector.service >/dev/null 2>&1 || true
