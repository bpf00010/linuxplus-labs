#!/usr/bin/env bash
set -euo pipefail

# Create sysadmin user if not present
id -u sysadmin &>/dev/null || useradd -m -s /bin/bash sysadmin
echo "sysadmin:linuxplus" | chpasswd
usermod -aG sudo sysadmin 2>/dev/null || true

# 1. Set up broken dnsmasq configuration (scoped, 127.0.0.1:18053 only)
mkdir -p /etc/lab-dns

# Broken config: wrong IP for db.lab.internal, plus invalid option
cat > /etc/lab-dns/dnsmasq.conf <<'DNSCONF'
# Lab DNS Configuration - scoped to loopback only
listen-address=127.0.0.1
port=18053
bind-interfaces
no-resolv
no-hosts
bogus-option-that-does-not-exist=true
address=/db.lab.internal/10.99.99.99
txt-record=status.lab.internal,"operational"
DNSCONF

# Create scoped systemd service for lab-dns
cat > /etc/systemd/system/lab-dns.service <<'UNIT'
[Unit]
Description=Lab DNS Service (scoped dnsmasq on 127.0.0.1:18053)
After=network.target

[Service]
Type=simple
ExecStart=/usr/sbin/dnsmasq --no-daemon --conf-file=/etc/lab-dns/dnsmasq.conf
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload 2>/dev/null || true
systemctl stop lab-dns.service 2>/dev/null || true
systemctl disable lab-dns.service 2>/dev/null || true

# 2. Create broken socket-activation pair
# The echo service script
mkdir -p /usr/local/lib/lab-diag
cat > /usr/local/lib/lab-diag/echo-diag.py <<'PYECHO'
#!/usr/bin/env python3
"""Simple socket-activated echo service returning DIAG_OK."""
import sys
sys.stdout.write("DIAG_OK\n")
sys.stdout.flush()
PYECHO
chmod +x /usr/local/lib/lab-diag/echo-diag.py

# Socket unit with WRONG port (18071 instead of 18070)
cat > /etc/systemd/system/diag-echo.socket <<'SOCKET'
[Unit]
Description=Diagnostic Echo Socket

[Socket]
ListenStream=127.0.0.1:18071
Accept=yes

[Install]
WantedBy=sockets.target
SOCKET

# Service template for socket activation
cat > '/etc/systemd/system/diag-echo@.service' <<'SVC'
[Unit]
Description=Diagnostic Echo Service Instance

[Service]
Type=simple
StandardInput=socket
StandardOutput=socket
ExecStart=/usr/local/lib/lab-diag/echo-diag.py
SVC

systemctl daemon-reload 2>/dev/null || true
systemctl stop diag-echo.socket 2>/dev/null || true
systemctl disable diag-echo.socket 2>/dev/null || true

# 3. Generate synthetic access log with deterministic 500 errors
# Use a fixed seed approach for reproducible results
cat > /tmp/gen-access-log.py <<'GENLOG'
import random
import datetime

random.seed(42)

client_ips = [
    "192.168.1.10",
    "192.168.1.22",
    "192.168.1.35",
    "10.0.0.5",
    "10.0.0.17",
    "172.16.0.100",
]

paths = ["/api/data", "/api/health", "/api/users", "/dashboard", "/login", "/api/reports"]
methods = ["GET", "POST", "GET", "GET", "POST", "GET"]

lines = []
base_time = datetime.datetime(2026, 11, 20, 8, 0, 0)

for i in range(200):
    ts = base_time + datetime.timedelta(seconds=i * 30)
    ts_str = ts.strftime("%d/%b/%Y:%H:%M:%S +0000")
    ip = random.choice(client_ips)
    path_idx = random.randint(0, len(paths) - 1)
    method = methods[path_idx]
    path = paths[path_idx]

    # Make 10.0.0.17 the top 500 offender with ~25 errors
    if ip == "10.0.0.17" and random.random() < 0.55:
        status = 500
    elif ip == "192.168.1.35" and random.random() < 0.25:
        status = 500
    elif random.random() < 0.03:
        status = 500
    elif random.random() < 0.1:
        status = 404
    elif random.random() < 0.05:
        status = 403
    else:
        status = 200

    size = random.randint(128, 8192)
    lines.append(f'{ip} - - [{ts_str}] "{method} {path} HTTP/1.1" {status} {size}')

with open("/var/log/lab-access.log", "w") as f:
    f.write("\n".join(lines) + "\n")
GENLOG

python3 /tmp/gen-access-log.py
rm -f /tmp/gen-access-log.py

# Remove any stale incident summary
rm -f /var/tmp/incident-summary.json
