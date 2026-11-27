#!/usr/bin/env bash
set -euo pipefail

# 1. Create group devteam and user dev1
getent group devteam >/dev/null 2>&1 || groupadd devteam
id -u dev1 >/dev/null 2>&1 || useradd -m -s /bin/bash -g devteam dev1

# 2. Plant insecure SUID binary
cp /bin/cat /usr/local/bin/legacy-helper
chown root:root /usr/local/bin/legacy-helper
chmod 4755 /usr/local/bin/legacy-helper

# 3. Create /srv/dropbox with bad permissions (0777 root:root)
mkdir -p /srv/dropbox
chown root:root /srv/dropbox
chmod 0777 /srv/dropbox

# 4. Create /srv/app files and broken symlink
mkdir -p /srv/app
cat <<'EOF' > /srv/app/config.v2
port=8080
mode=production
EOF
cat <<'EOF' > /srv/app/readme.txt
Application documentation
EOF
rm -f /srv/app/readme.hard /srv/app/current.conf
ln -s /srv/app/config.v1 /srv/app/current.conf

# 5. Plant umask 0000 in /home/dev1/.bashrc
touch /home/dev1/.bashrc
sed -i '/^[[:space:]]*umask\b/d' /home/dev1/.bashrc
echo "umask 0000" >> /home/dev1/.bashrc
chown dev1:devteam /home/dev1/.bashrc
