#!/usr/bin/env bash
set -euo pipefail

# 1. Clean skel, limits, appuser, and ops group
rm -rf /etc/skel/WELCOME.txt /etc/skel/bin /etc/security/limits.d/99-appuser.conf
userdel -r appuser >/dev/null 2>&1 || true
groupdel ops >/dev/null 2>&1 || true

# 2. Create unlocked active formeremp account with no expiration
id -u formeremp >/dev/null 2>&1 || useradd -m -s /bin/bash formeremp
usermod -s /bin/bash formeremp
echo 'formeremp:TempPass123!' | chpasswd
usermod -U formeremp >/dev/null 2>&1 || true
chage -E -1 formeremp
