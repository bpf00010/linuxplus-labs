#!/usr/bin/env bash
set -euo pipefail

# 1. Topology provisioning script
mkdir -p /usr/local/bin
cat <<'EOF' > /usr/local/bin/netns-setup.sh
#!/usr/bin/env bash
set -euo pipefail

# Create namespace
ip netns add app-ns 2>/dev/null || true

# Recreate veth pair
ip link del veth-host 2>/dev/null || true
ip link add veth-host type veth peer name veth-app
ip link set veth-app netns app-ns

# Configure root end
ip addr flush dev veth-host 2>/dev/null || true
ip addr add 10.250.10.1/24 dev veth-host
ip link set veth-host up

# Configure namespace end (deliberately left DOWN with NO default route)
ip netns exec app-ns ip addr flush dev veth-app 2>/dev/null || true
ip netns exec app-ns ip addr add 10.250.10.2/24 dev veth-app
ip netns exec app-ns ip link set lo up
ip netns exec app-ns ip link set veth-app down

# Install scoped firewall table inside app-ns dropping port 18090
ip netns exec app-ns nft delete table inet app_fw 2>/dev/null || true
ip netns exec app-ns nft add table inet app_fw
ip netns exec app-ns nft 'add chain inet app_fw input { type filter hook input priority 0; policy accept; }'
ip netns exec app-ns nft add rule inet app_fw input tcp dport 18090 drop
EOF
chmod 755 /usr/local/bin/netns-setup.sh

# 2. Systemd topology unit
cat <<'EOF' > /etc/systemd/system/netns-topology.service
[Unit]
Description=Network Namespace Topology Provisioner
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/netns-setup.sh

[Install]
WantedBy=multi-user.target
EOF

# 3. Systemd API server unit inside app-ns
cat <<'EOF' > /etc/systemd/system/netns-api.service
[Unit]
Description=Network Namespace Health API Server
After=netns-topology.service
Wants=netns-topology.service

[Service]
Type=simple
ExecStart=/sbin/ip netns exec app-ns /usr/bin/python3 -c "import http.server, socketserver; \
class H(http.server.BaseHTTPRequestHandler): \
    def do_GET(self): \
        self.send_response(200); \
        self.send_header('Content-Type','application/json'); \
        self.end_headers(); \
        self.wfile.write(b'{\"status\":\"healthy\",\"netns\":\"app-ns\"}\n'); \
    def log_message(self, *a): pass; \
socketserver.TCPServer(('10.250.10.2', 18090), H).serve_forever()"
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

# Run setup and enable services
systemctl daemon-reload >/dev/null 2>&1 || true
/usr/local/bin/netns-setup.sh
systemctl enable --now netns-topology.service >/dev/null 2>&1 || true
systemctl enable --now netns-api.service >/dev/null 2>&1 || true
