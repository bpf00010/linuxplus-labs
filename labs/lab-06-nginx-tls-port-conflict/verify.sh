#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="legacy-stub.service is inactive and disabled"
chk1_det=""

chk2_pass=false
chk2_desc="/etc/ssl/portal/portal.key is owned by root:root with mode 600"
chk2_det=""

chk3_pass=false
chk3_desc="nginx -t passes validation and nginx.service is active and enabled"
chk3_det=""

chk4_pass=false
chk4_desc="Endpoint https://127.0.0.1:18443/ returns HTTP 200 containing healthy"
chk4_det=""

# Check 1: legacy-stub stopped and disabled
stub_active=true
stub_enabled=true

if ! systemctl is-active legacy-stub.service >/dev/null 2>&1; then
    stub_active=false
fi

if ! systemctl is-enabled legacy-stub.service >/dev/null 2>&1; then
    stub_enabled=false
fi

if [ "$stub_active" = false ] && [ "$stub_enabled" = false ]; then
    chk1_pass=true
    chk1_det="legacy-stub.service is successfully stopped and disabled."
else
    chk1_det="legacy-stub status: active=${stub_active}, enabled=${stub_enabled}"
fi

# Check 2: TLS key permissions and ownership
key_path="/etc/ssl/portal/portal.key"
owner=""
mode=""

if [ -f "$key_path" ]; then
    owner=$(stat -c "%U:%G" "$key_path" 2>/dev/null || echo "")
    mode=$(stat -c "%a" "$key_path" 2>/dev/null || echo "")
fi

if [ "$owner" = "root:root" ] && [ "$mode" = "600" ]; then
    chk2_pass=true
    chk2_det="Private key ${key_path} is securely owned by root:root with mode 600."
else
    chk2_det="Private key status: owner=${owner}, mode=${mode} (expected root:root, 600)"
fi

# Check 3: Nginx syntax and service status
nginx_syntax=false
nginx_active=false
nginx_enabled=false

if nginx -t >/dev/null 2>&1; then
    nginx_syntax=true
fi

if systemctl is-active nginx >/dev/null 2>&1; then
    nginx_active=true
fi

if systemctl is-enabled nginx >/dev/null 2>&1; then
    nginx_enabled=true
fi

if [ "$nginx_syntax" = true ] && [ "$nginx_active" = true ] && [ "$nginx_enabled" = true ]; then
    chk3_pass=true
    chk3_det="Nginx configuration passes syntax test and service is enabled and active."
else
    chk3_det="Nginx: syntax=${nginx_syntax}, active=${nginx_active}, enabled=${nginx_enabled}"
fi

# Check 4: HTTPS request to reverse proxy
curl_ok=false
http_out=""
if command -v curl >/dev/null 2>&1; then
    http_out=$(curl -kfsS --max-time 3 https://127.0.0.1:18443/ 2>/dev/null || echo "")
    if echo "$http_out" | grep -E "healthy" >/dev/null 2>&1; then
        curl_ok=true
    fi
fi

if [ "$curl_ok" = true ]; then
    chk4_pass=true
    chk4_det="HTTPS request to https://127.0.0.1:18443/ succeeded with response: ${http_out}"
else
    chk4_det="Failed to retrieve HTTP 200 with 'healthy' from https://127.0.0.1:18443/"
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
  "lab_id": "lab-06",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-stub-disabled",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-tls-key-perms",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-nginx-service",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-https-proxy-pass",
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
