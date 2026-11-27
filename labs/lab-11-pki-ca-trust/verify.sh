#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="Does portal.key have mode 0600 and does portal.crt verify against /etc/lab-ca/ca.crt?"
chk1_det=""

chk2_pass=false
chk2_desc="Does portal.crt contain SAN DNS:portal.lab.internal?"
chk2_det=""

chk3_pass=false
chk3_desc="Is lab-ca.crt installed in the system trust store and is nginx.service active?"
chk3_det=""

chk4_pass=false
chk4_desc="Does curl https://portal.lab.internal:18450/ succeed without -k and return trusted?"
chk4_det=""

# Check 1: Key permissions and cert verification
key_mode=$(stat -c '%a' /etc/ssl/lab-portal/portal.key 2>/dev/null || echo "")
cert_verify=false
openssl verify -CAfile /etc/lab-ca/ca.crt /etc/ssl/lab-portal/portal.crt >/dev/null 2>&1 && cert_verify=true

if [ "$key_mode" = "600" ] && [ "$cert_verify" = true ]; then
    chk1_pass=true
    chk1_det="portal.key mode 0600 and portal.crt signed by CA."
else
    chk1_det="key_mode=${key_mode}, cert_verifies=${cert_verify}"
fi

# Check 2: SAN contains DNS:portal.lab.internal
san_check=false
openssl x509 -in /etc/ssl/lab-portal/portal.crt -noout -text 2>/dev/null | grep -q 'DNS:portal.lab.internal' && san_check=true

if [ "$san_check" = true ]; then
    chk2_pass=true
    chk2_det="SAN DNS:portal.lab.internal present."
else
    chk2_det="Missing SAN DNS:portal.lab.internal."
fi

# Check 3: CA installed in trust store and nginx active
ca_installed=false
ca_match=false
nginx_active=false

if [ -f /usr/local/share/ca-certificates/lab-ca.crt ]; then
    ca_installed=true
    ca_hash=$(sha256sum /etc/lab-ca/ca.crt 2>/dev/null | awk '{print $1}')
    installed_hash=$(sha256sum /usr/local/share/ca-certificates/lab-ca.crt 2>/dev/null | awk '{print $1}')
    [ "$ca_hash" = "$installed_hash" ] && [ -n "$ca_hash" ] && ca_match=true
fi
systemctl is-active nginx.service >/dev/null 2>&1 && nginx_active=true

if [ "$ca_installed" = true ] && [ "$ca_match" = true ] && [ "$nginx_active" = true ]; then
    chk3_pass=true
    chk3_det="lab-ca.crt installed and nginx.service active."
else
    chk3_det="ca_installed=${ca_installed}, ca_matches=${ca_match}, nginx_active=${nginx_active}"
fi

# Check 4: curl succeeds without -k
curl_result=$(curl -fsS --max-time 3 https://portal.lab.internal:18450/ 2>/dev/null || echo "CURL_FAILED")
if echo "$curl_result" | grep -q '"trusted"'; then
    chk4_pass=true
    chk4_det="HTTPS request trusted without -k."
else
    safe_curl=$(printf '%s' "$curl_result" | tr -d '\r\n"\\' | head -c 120)
    chk4_det="curl=${safe_curl}"
fi

score_passed=0
[ "$chk1_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk2_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk3_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk4_pass" = true ] && score_passed=$((score_passed + 1))

overall_passed=false
[ "$score_passed" -eq 4 ] && overall_passed=true

cat <<EOF
{
  "lab_id": "lab-11",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-key-cert-verify",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-san-entry",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-ca-trust-nginx",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-curl-trusted",
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
