#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="veth-host and veth-app (in app-ns) are UP with 10.250.10.1/24 and 10.250.10.2/24"
chk1_det=""

chk2_pass=false
chk2_desc="app-ns has a valid default route via 10.250.10.1"
chk2_det=""

chk3_pass=false
chk3_desc="curl http://10.250.10.2:18090/health returns HTTP 200 ok from root namespace"
chk3_det=""

# Check 1: Interface state and IP addresses
host_link_up=false
host_ip_ok=false
app_link_up=false
app_ip_ok=false

if ip link show veth-host 2>/dev/null | grep -q "state UP"; then
    host_link_up=true
fi
if ip addr show veth-host 2>/dev/null | grep -q "10\.250\.10\.1/24"; then
    host_ip_ok=true
fi

if ip netns exec app-ns ip link show veth-app 2>/dev/null | grep -q "state UP"; then
    app_link_up=true
fi
if ip netns exec app-ns ip addr show veth-app 2>/dev/null | grep -q "10\.250\.10\.2/24"; then
    app_ip_ok=true
fi

if [ "$host_link_up" = true ] && [ "$host_ip_ok" = true ] && [ "$app_link_up" = true ] && [ "$app_ip_ok" = true ]; then
    chk1_pass=true
    chk1_det="Both veth interfaces are UP with assigned 10.250.10.0/24 subnet addresses."
else
    chk1_det="host_up=${host_link_up}, host_ip=${host_ip_ok}, app_up=${app_link_up}, app_ip=${app_ip_ok}"
fi

# Check 2: Default gateway route in app-ns
route_ok=false
if ip netns exec app-ns ip route show 2>/dev/null | grep -q "default via 10\.250\.10\.1"; then
    route_ok=true
fi

if [ "$route_ok" = true ]; then
    chk2_pass=true
    chk2_det="Default route via 10.250.10.1 exists in app-ns."
else
    chk2_det="Missing default via 10.250.10.1 route in app-ns."
fi

# Check 3: HTTP Health endpoint reachability from root namespace
curl_ok=false

# Ensure server is running in background inside app-ns if it terminated
if ! ip netns exec app-ns pgrep -f "microservice\.py" >/dev/null 2>&1; then
    nohup ip netns exec app-ns python3 /var/lib/lplab/microservice.py >/dev/null 2>&1 &
    sleep 1
fi

resp=$(curl -fsS --max-time 3 http://10.250.10.2:18090/health 2>/dev/null || echo "")
if echo "$resp" | grep -q '"status":"ok"'; then
    curl_ok=true
fi

if [ "$curl_ok" = true ]; then
    chk3_pass=true
    chk3_det="Microservice responded with HTTP 200 and healthy payload."
else
    chk3_det="Failed to reach http://10.250.10.2:18090/health from root namespace."
fi

# Calculate score
score_passed=0
[ "$chk1_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk2_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk3_pass" = true ] && score_passed=$((score_passed + 1))
score_total=3

overall_passed=false
[ "$score_passed" -eq "$score_total" ] && overall_passed=true

# Output strict JSON
cat <<EOF
{
  "lab_id": "lab-06",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": ${score_total},
  "checks": [
    {
      "id": "chk-links",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-route",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-endpoint",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    }
  ]
}
EOF

if [ "$overall_passed" = true ]; then
    exit 0
else
    exit 1
fi
