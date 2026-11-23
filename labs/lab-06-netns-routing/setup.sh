#!/usr/bin/env bash
set -euo pipefail

# 1. Clean previous state
ip netns del app-ns 2>/dev/null || true
ip link del veth-host 2>/dev/null || true
pkill -f "python3.*microservice.py" 2>/dev/null || true

# 2. Create isolated network namespace
ip netns add app-ns

# 3. Create veth peer link
ip link add veth-host type veth peer name veth-app
ip link set veth-app netns app-ns

# 4. Configure veth-host in root namespace
ip addr add 10.250.10.1/24 dev veth-host
ip link set veth-host up

# 5. Configure veth-app inside app-ns (BREAKAGES: left DOWN, no default route)
ip netns exec app-ns ip addr add 10.250.10.2/24 dev veth-app
# veth-app is left DOWN deliberately
ip netns exec app-ns ip link set lo up
# Default route via 10.250.10.1 omitted deliberately

# 6. Scoped nftables drop rule INSIDE app-ns (zero impact on root namespace)
ip netns exec app-ns nft delete table inet ns_filter 2>/dev/null || true
ip netns exec app-ns nft add table inet ns_filter
ip netns exec app-ns nft 'add chain inet ns_filter input { type filter hook input priority 0; policy accept; }'
ip netns exec app-ns nft add rule inet ns_filter input tcp dport 18090 drop

# 7. Start microservice HTTP daemon inside app-ns
mkdir -p /var/lib/lplab
cat <<'EOF' > /var/lib/lplab/microservice.py
import http.server
import socketserver
import sys

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","service":"isolated-microservice"}\n')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Silent

server_address = ("10.250.10.2", 18090)
try:
    with socketserver.TCPServer(server_address, HealthHandler) as httpd:
        httpd.serve_forever()
except Exception:
    sys.exit(0)
EOF

nohup ip netns exec app-ns python3 /var/lib/lplab/microservice.py >/dev/null 2>&1 &
