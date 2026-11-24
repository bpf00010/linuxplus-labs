#!/usr/bin/env bash
set -euo pipefail

# 1. Create sparse 32MB ext4 loop image
mkdir -p /var/lib/lplab /mnt/archive
dd if=/dev/zero of=/var/lib/lplab/archive.img bs=1M count=32 status=none
mkfs.ext4 -F /var/lib/lplab/archive.img >/dev/null 2>&1

# 2. Plant broken native systemd mount unit (wrong What= path, missing security options)
cat <<'EOF' > /etc/systemd/system/mnt-archive.mount
[Unit]
Description=Secure Archive Storage Mount
DefaultDependencies=no
Conflicts=umount.target
Before=local-fs.target umount.target

[Mount]
What=/var/lib/lplab/archive-wrong.img
Where=/mnt/archive
Type=ext4
Options=loop

[Install]
WantedBy=multi-user.target
EOF

# 3. Create companion service that depends on mount unit
cat <<'EOF' > /etc/systemd/system/archive-sync.service
[Unit]
Description=Archive Synchronization Service
Requires=mnt-archive.mount
After=mnt-archive.mount

[Service]
Type=simple
ExecStart=/bin/sh -c "while true; do touch /mnt/archive/sync.lock 2>/dev/null || true; sleep 5; done"
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd, ensure units are unmounted and disabled
systemctl daemon-reload >/dev/null 2>&1 || true
umount /mnt/archive >/dev/null 2>&1 || true
systemctl disable mnt-archive.mount >/dev/null 2>&1 || true
systemctl stop mnt-archive.mount >/dev/null 2>&1 || true
systemctl disable archive-sync.service >/dev/null 2>&1 || true
systemctl stop archive-sync.service >/dev/null 2>&1 || true
