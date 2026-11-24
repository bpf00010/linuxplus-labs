#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="veth-host and veth-app (inside app-ns) interfaces are both UP"
chk1_det=""

chk2_pass=false
chk2_desc="Default route via 10.250.10.1 exists inside namespace app-ns"
chk2_det=""

chk3_pass=false
chk3_desc="netns-api.service is active and scoped table app_fw permits TCP 18090"
chk3_det=""

chk4_pass=false
chk4_desc="Endpoint http://10.250.10.2:18090/health returns HTTP 200 healthy from root namespace"
chk4_det=""

# Check 1: Interface state
host_up=false
app_up=false

if ip link show veth-host 2>/dev/null | grep -E "state (UP|UNKNOWN)" >/dev/null 2>&1; then
    host_up=true
fi

if ip netns exec app-ns ip link show veth-app 2>/dev/null | grep -E "state (UP|UNKNOWN)" >/dev/null 2>&1; then
    app_up=true
fi

if [ "$host_up" = true ] && [ "$app_up" = true ]; then
    chk1_pass=true
    chk1_det="Both veth-host and veth-app are in UP administrative state."
else
    chk1_det="Interface state: veth-host=${host_up}, veth-app=${app_up}"
fi

# Check 2: Default route in app-ns
route_ok=false
if ip netns exec app-ns ip route show 2>/dev/null | grep -E "default via 10\.250\.10\.1" >/dev/null 2>&1; then
    route_ok=true
fi

if [ "$route_ok" = true ]; then
    chk2_pass=true
    chk2_det="Default route via 10.250.10.1 is present inside app-ns."
else
    chk2_det="Default route via 10.250.10.1 is missing inside app-ns."
fi

# Check 3: Service active & scoped firewall drop rule removed
svc_active=false
fw_table_exists=false
drop_absent=false

if systemctl is-active netns-api.service >/dev/null 2>&1; then
    svc_active=true
fi

if ip netns exec app-ns nft list table inet app_fw >/dev/null 2>&1; then
    fw_table_exists=true
    if ! ip netns exec app-ns nft list table inet app_fw 2>/dev/null | grep -E "tcp dport 18090 drop" >/dev/null 2>&1; then
        drop_absent=true
    fi
fi

if [ "$svc_active" = true ] && [ "$fw_table_exists" = true ] && [ "$drop_absent" = true ]; then
    chk3_pass=true
    chk3_det="netns-api.service is active, inet app_fw table exists, and port 18090 drop rule is absent."
else
    chk3_det="Service active=${svc_active}, table_exists=${fw_table_exists}, drop_rule_absent=${drop_absent}"
fi

# Check 4: HTTP health query from root namespace
curl_ok=false
http_resp=""
if command -v curl >/dev/null 2>&1; then
    http_resp=$(curl -fsS --max-time 3 http://10.250.10.2:18090/health 2>/dev/null || echo "")
    if echo "$http_resp" | grep -E '"status"\s*:\s*"healthy"' >/dev/null 2>&1; then
        curl_ok=true
    fi
fi

if [ "$curl_ok" = true ]; then
    chk4_pass=true
    chk4_det="Root namespace reached http://10.250.10.2:18090/health successfully: ${http_resp}"
else
    chk4_det="Failed to receive HTTP 200 healthy from http://10.250.10.2:18090/health"
fi

# Calculate score
score_passed=0
[ "$chk1_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk2_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk3_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk4_pass" = true ] && score_passed=$((score_passed + 1))

overall_passed=false
[ "$score_passed" -eq 4 ] && overall_passed=true

cat <<EOF
{
  "lab_id": "lab-05",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-interfaces-up",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-default-route",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-firewall-service",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-health-endpoint",
      "description": "${chk4_desc}",
      "passed": ${chk4_pass},
      "details": "${chk4_det}"
    }
  ]
}
EOF

if [ "$overall_passed" = true ]; then
    exit 0
else
    exit 1
fi
