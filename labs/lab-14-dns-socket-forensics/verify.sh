#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="Is lab-dns.service enabled and active, and does db.lab.internal resolve to 10.20.30.40?"
chk1_det=""

chk2_pass=false
chk2_desc="Does the status.lab.internal TXT record return operational?"
chk2_det=""

chk3_pass=false
chk3_desc="Is diag-echo.socket enabled and active on 127.0.0.1:18070 and returning DIAG_OK?"
chk3_det=""

chk4_pass=false
chk4_desc="Does /var/tmp/incident-summary.json contain accurate top_ip and error_500_count?"
chk4_det=""

# Check 1: lab-dns.service active and DNS A record
dns_enabled=false
dns_active=false
dns_resolves=false

systemctl is-enabled lab-dns.service >/dev/null 2>&1 && dns_enabled=true
systemctl is-active lab-dns.service >/dev/null 2>&1 && dns_active=true

dig_result=$(dig @127.0.0.1 -p 18053 db.lab.internal +short 2>/dev/null || echo "")
if [ "$dig_result" = "10.20.30.40" ]; then
    dns_resolves=true
fi

if [ "$dns_enabled" = true ] && [ "$dns_active" = true ] && [ "$dns_resolves" = true ]; then
    chk1_pass=true
    chk1_det="lab-dns.service active and db.lab.internal resolves to 10.20.30.40."
else
    safe_dig=$(printf '%s' "$dig_result" | tr -d '\r\n"\\' | head -c 100)
    chk1_det="enabled=${dns_enabled}, active=${dns_active}, resolves=${dns_resolves} (got: ${safe_dig})"
fi

# Check 2: TXT record for status.lab.internal
txt_result=$(dig @127.0.0.1 -p 18053 status.lab.internal TXT +short 2>/dev/null || echo "")
if echo "$txt_result" | grep -qi 'operational'; then
    chk2_pass=true
    chk2_det="TXT record returns operational."
else
    safe_txt=$(printf '%s' "$txt_result" | tr -d '\r\n"\\' | head -c 100)
    chk2_det="TXT=${safe_txt}"
fi

# Check 3: diag-echo.socket
sock_enabled=false
sock_active=false
echo_ok=false

systemctl is-enabled diag-echo.socket >/dev/null 2>&1 && sock_enabled=true
systemctl is-active diag-echo.socket >/dev/null 2>&1 && sock_active=true

sock_port=$(systemctl show diag-echo.socket -p Listen 2>/dev/null | grep -o '127\.0\.0\.1:18070' || echo "")

echo_response=$(socat -t 2 -T 2 - TCP:127.0.0.1:18070,connect-timeout=2 </dev/null 2>/dev/null || echo "")
if echo "$echo_response" | grep -q 'DIAG_OK'; then
    echo_ok=true
fi

if [ "$sock_enabled" = true ] && [ "$sock_active" = true ] && [ -n "$sock_port" ] && [ "$echo_ok" = true ]; then
    chk3_pass=true
    chk3_det="diag-echo.socket active on 127.0.0.1:18070 and returns DIAG_OK."
else
    chk3_det="enabled=${sock_enabled}, active=${sock_active}, port18070=$([ -n "$sock_port" ] && echo true || echo false), echo=${echo_ok}"
fi

# Check 4: incident-summary.json matches ground truth
if [ -f /var/tmp/incident-summary.json ] && [ -f /var/log/lab-access.log ]; then
    gt_top_ip=$(awk '$9 == 500 {count[$1]++} END {max=0; for(ip in count) if(count[ip]>max){max=count[ip]; top=ip} print top}' /var/log/lab-access.log)
    gt_count=$(awk -v ip="$gt_top_ip" '$1 == ip && $9 == 500 {c++} END {print c+0}' /var/log/lab-access.log)

    student_ip=$(python3 -c "import json; d=json.load(open('/var/tmp/incident-summary.json')); print(str(d.get('top_ip','')))" 2>/dev/null | tr -d '\r\n"\\' | head -c 64 || echo "")
    student_count=$(python3 -c "import json; d=json.load(open('/var/tmp/incident-summary.json')); print(d.get('error_500_count',0))" 2>/dev/null | tr -d '\r\n"\\' | head -c 16 || echo "0")

    if [ "$student_ip" = "$gt_top_ip" ] && [ "$student_count" = "$gt_count" ]; then
        chk4_pass=true
        chk4_det="top_ip=${student_ip}, error_500_count=${student_count}."
    else
        chk4_det="got ip=${student_ip} count=${student_count}, expected ip=${gt_top_ip} count=${gt_count}"
    fi
else
    chk4_det="Missing /var/tmp/incident-summary.json or /var/log/lab-access.log"
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
  "lab_id": "lab-14",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-dns-service",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-dns-txt",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-socket-activation",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-incident-summary",
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
