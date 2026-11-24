#!/usr/bin/env bash
set -euo pipefail

# 1. Install batch worker script (allocates ~40MB RAM and 64 file descriptors)
mkdir -p /usr/local/bin
cat <<'EOF' > /usr/local/bin/batch-worker.py
#!/usr/bin/env python3
import time
import os

try:
    # Open 64 file descriptors
    fds = [os.open("/dev/null", os.O_RDONLY) for _ in range(64)]
    # Allocate 40MB heap
    payload = bytearray(40 * 1024 * 1024)
except Exception as e:
    print(f"Worker startup failed: {e}")
    raise

while True:
    time.sleep(5)
EOF
chmod 755 /usr/local/bin/batch-worker.py

# 2. Create batch-worker systemd unit
cat <<'EOF' > /etc/systemd/system/batch-worker.service
[Unit]
Description=Batch Processing Worker
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/batch-worker.py
Restart=no

[Install]
WantedBy=multi-user.target
EOF

# 3. Inject broken drop-in with unachievable limits (8M RAM, 32 fds)
mkdir -p /etc/systemd/system/batch-worker.service.d
cat <<'EOF' > /etc/systemd/system/batch-worker.service.d/override.conf
[Service]
MemoryMax=8M
LimitNOFILE=32
EOF

# 4. Create runaway rogue logger
cat <<'EOF' > /etc/systemd/system/rogue-logger.service
[Unit]
Description=Rogue Logging Daemon
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -c "import time; \
while True: \
    with open('/var/log/rogue.log', 'a') as f: f.write('spamming logs\n'); \
    time.sleep(1)"
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 5. Plant poor sysctl parameters
mkdir -p /etc/sysctl.d
cat <<'EOF' > /etc/sysctl.d/99-lab-perf.conf
vm.swappiness = 95
fs.inotify.max_user_watches = 8192
EOF

# Apply sysctl initial state (ignore errors in WSL)
sysctl -p /etc/sysctl.d/99-lab-perf.conf >/dev/null 2>&1 || true

# Reload systemd and start rogue logger, attempt worker start
systemctl daemon-reload >/dev/null 2>&1 || true
systemctl start rogue-logger.service >/dev/null 2>&1 || true
systemctl enable rogue-logger.service >/dev/null 2>&1 || true
systemctl start batch-worker.service >/dev/null 2>&1 || true
