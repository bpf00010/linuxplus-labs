#!/usr/bin/env bash
set -euo pipefail

# Create sysadmin user if not present
id -u sysadmin &>/dev/null || useradd -m -s /bin/bash sysadmin
echo "sysadmin:linuxplus" | chpasswd

# 1. Create the golden backup tarball
STAGE=$(mktemp -d)
mkdir -p "${STAGE}/app-prod/bin"

cat > "${STAGE}/app-prod/app.conf" <<'APPCONF'
[application]
name = ops-dashboard
port = 8080
log_level = info
data_dir = /var/lib/ops-dashboard
APPCONF

cat > "${STAGE}/app-prod/bin/run.sh" <<'RUNSH'
#!/usr/bin/env bash
set -euo pipefail
echo "Starting ops-dashboard..."
source /srv/app-prod/app.conf 2>/dev/null || true
echo "Dashboard running on port 8080"
RUNSH
chmod 755 "${STAGE}/app-prod/bin/run.sh"

# Create symlink
ln -sf app.conf "${STAGE}/app-prod/current.conf"

# Generate SHA256SUMS (relative paths)
cd "${STAGE}/app-prod"
sha256sum app.conf bin/run.sh > SHA256SUMS
cd /

# Create tarball preserving permissions and symlinks
tar czf /var/backups/app-release.tar.gz -C "${STAGE}" app-prod/
rm -rf "${STAGE}"

# 2. Corrupt /srv/app-prod/
mkdir -p /srv/app-prod/bin /srv/app-prod/cache

# Overwrite app.conf with garbage
echo "CORRUPTED_DATA_GARBAGE_12345" > /srv/app-prod/app.conf

# Delete run.sh
rm -f /srv/app-prod/bin/run.sh

# Break symlink
rm -f /srv/app-prod/current.conf
echo "broken_link_target" > /srv/app-prod/current.conf

# Drop junk files
echo "debug output 12345" > /srv/app-prod/debug.tmp
echo "stale cache data" > /srv/app-prod/cache/stale.bin

# Remove SHA256SUMS so student must restore it
rm -f /srv/app-prod/SHA256SUMS

# 3. Create empty backup mirror directory
mkdir -p /srv/backup-mirror
mkdir -p /var/backups
