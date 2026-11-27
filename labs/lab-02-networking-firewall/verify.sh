#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="Does nginx -t pass and is nginx.service active?"
chk1_det=""

chk2_pass=false
chk2_desc="Does /etc/hosts map api.lab.internal to 127.0.0.1?"
chk2_det=""

chk3_pass=false
chk3_desc="Does nftables table inet lplab02 exist and allow TCP port 18080?"
chk3_det=""

chk4_pass=false
chk4_desc="Does http://api.lab.internal:18080/health return HTTP 200 healthy?"
chk4_det=""

# Check 1: Nginx syntax and service status
nginx_syntax=false
if nginx -t >/dev/null 2>&1; then
    nginx_syntax=true
fi

nginx_active=false
if systemctl is-active nginx >/dev/null 2>&1; then
    nginx_active=true
fi

if [ "$nginx_syntax" = true ] && [ "$nginx_active" = true ]; then
    chk1_pass=true
    chk1_det="nginx -t passed and nginx is active."
else
    chk1_det="syntax_ok=${nginx_syntax}, active=${nginx_active}"
fi

# Check 2: /etc/hosts mapping
hosts_ok=false
if grep -E "^127\.0\.0\.1\s+.*api\.lab\.internal" /etc/hosts >/dev/null 2>&1; then
    hosts_ok=true
fi

if [ "$hosts_ok" = true ]; then
    chk2_pass=true
    chk2_det="api.lab.internal maps to 127.0.0.1 in /etc/hosts."
else
    chk2_det="api.lab.internal is not mapped to 127.0.0.1 in /etc/hosts."
fi

# Check 3: Scoped nftables table
table_exists=false
drop_rule_absent=false

if nft list table inet lplab02 >/dev/null 2>&1; then
    table_exists=true
    if ! nft list table inet lplab02 2>/dev/null | grep -E "tcp dport 18080 drop" >/dev/null 2>&1; then
        drop_rule_absent=true
    fi
fi

if [ "$table_exists" = true ] && [ "$drop_rule_absent" = true ]; then
    chk3_pass=true
    chk3_det="table inet lplab02 exists and port 18080 is allowed."
else
    chk3_det="table_exists=${table_exists}, drop_removed=${drop_rule_absent}"
fi

# Check 4: HTTP health endpoint
curl_ok=false
resp_body=$(curl -fsS --max-time 3 http://api.lab.internal:18080/health 2>/dev/null || true)
if echo "$resp_body" | grep -q '"status":"healthy"'; then
    curl_ok=true
fi

if [ "$curl_ok" = true ]; then
    chk4_pass=true
    chk4_det="Health endpoint returned HTTP 200 healthy."
else
    chk4_det="Request to http://api.lab.internal:18080/health failed."
fi

score_passed=0
[ "$chk1_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk2_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk3_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk4_pass" = true ] && score_passed=$((score_passed + 1))
score_total=4

overall_passed=false
[ "$score_passed" -eq "$score_total" ] && overall_passed=true

cat <<EOF
{
  "lab_id": "lab-02",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": ${score_total},
  "checks": [
    {
      "id": "chk-nginx",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-hosts",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-firewall",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-endpoint",
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
