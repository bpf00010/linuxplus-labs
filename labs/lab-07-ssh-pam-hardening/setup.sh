#!/usr/bin/env bash
set -euo pipefail

# 1. Create group sshusers and user opsadmin
groupadd -f sshusers
id -u opsadmin >/dev/null 2>&1 || useradd -m -s /bin/bash opsadmin
echo 'opsadmin:linuxplus' | chpasswd

# Set insecure password max age
chage -M 99999 opsadmin

# 2. Plant insecure .ssh folder and authorized_keys owned by root
mkdir -p /home/opsadmin/.ssh
chown root:root /home/opsadmin/.ssh
chmod 777 /home/opsadmin/.ssh

cat <<'EOF' > /home/opsadmin/.ssh/authorized_keys
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGtQ92y48p5R2cR9E7Zk1V2x8P3v4Q9Z7Y1X5W3V2U1T audit-compliance-key
EOF
chown root:root /home/opsadmin/.ssh/authorized_keys
chmod 666 /home/opsadmin/.ssh/authorized_keys

# 3. Drop insecure sshd configuration drop-in
mkdir -p /etc/ssh/sshd_config.d /run/sshd
cat <<'EOF' > /etc/ssh/sshd_config.d/99-lab-audit.conf
# SECURITY VIOLATION: Insecure SSH defaults
PermitRootLogin yes
PasswordAuthentication yes
EOF

# Restart SSH service
systemctl daemon-reload >/dev/null 2>&1 || true
systemctl restart ssh >/dev/null 2>&1 || systemctl restart ssh.socket >/dev/null 2>&1 || true
