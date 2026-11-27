#!/usr/bin/env bash
set -euo pipefail

# 1. Clean any prior package or output
dpkg -r lplab-tool >/dev/null 2>&1 || true
rm -f /var/tmp/curl-owner.txt /var/tmp/lplab-tool_1.0_all.deb

# 2. Build tiny offline .deb package using dpkg-deb
STAGE=$(mktemp -d)
mkdir -p "${STAGE}/DEBIAN" "${STAGE}/usr/local/bin"

cat <<'EOF' > "${STAGE}/DEBIAN/control"
Package: lplab-tool
Version: 1.0
Section: utils
Priority: optional
Architecture: all
Maintainer: Lab Admin <admin@lab.internal>
Description: Offline test package for Linux+ lab
EOF

cat <<'EOF' > "${STAGE}/usr/local/bin/lplab-tool"
#!/usr/bin/env bash
echo "lplab-tool 1.0"
EOF
chmod 0755 "${STAGE}/usr/local/bin/lplab-tool"

dpkg-deb --build "${STAGE}" /var/tmp/lplab-tool_1.0_all.deb >/dev/null 2>&1
chmod 0644 /var/tmp/lplab-tool_1.0_all.deb
rm -rf "${STAGE}"

# 3. Drop broken APT source list
mkdir -p /etc/apt/sources.list.d
echo "deb-broken http://invalid.local/ stable" > /etc/apt/sources.list.d/broken-internal.list

# 4. Hold package jq
apt-mark hold jq >/dev/null 2>&1 || true
