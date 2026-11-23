#!/usr/bin/env bash
set -euo pipefail

# 1. Create sshusers group and opsadmin user
getent group sshusers >/dev/null 2>&1 || groupadd sshusers
id -u opsadmin >/dev/null 2>&1 || useradd -m -s /bin/bash opsadmin
# Ensure opsadmin is NOT initially in sshusers (student must add)
gpasswd -d opsadmin sshusers >/dev/null 2>&1 || true

# 2. Seed opsadmin SSH directory with wide-open insecure permissions
mkdir -p /home/opsadmin/.ssh
if [ ! -f /home/opsadmin/.ssh/id_ed25519 ]; then
    ssh-keygen -t ed25519 -N "" -f /home/opsadmin/.ssh/id_ed25519 <<< y >/dev/null 2>&1
fi
cp /home/opsadmin/.ssh/id_ed25519.pub /home/opsadmin/.ssh/authorized_keys

# Plant insecure permissions and wrong ownership
chmod 777 /home/opsadmin/.ssh
chown root:root /home/opsadmin/.ssh/authorized_keys
chmod 666 /home/opsadmin/.ssh/authorized_keys

# 3. Write insecure sshd drop-in configuration
mkdir -p /etc/ssh/sshd_config.d
cat <<'EOF' > /etc/ssh/sshd_config.d/99-lab-audit.conf
# INSECURE AUDIT CONFIGURATION
PermitRootLogin yes
PasswordAuthentication yes
EOF

# Ensure sshd drop-in directory is included in main sshd_config
if ! grep -q "Include /etc/ssh/sshd_config.d/\*\.conf" /etc/ssh/sshd_config; then
    echo "Include /etc/ssh/sshd_config.d/*.conf" >> /etc/ssh/sshd_config
fi

# 4. Plant lax password aging policy (99999 days)
chage -M 99999 opsadmin >/dev/null 2>&1 || true
