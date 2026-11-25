#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="ansible-playbook --syntax-check site.yml passes"
chk1_det=""

chk2_pass=false
chk2_desc="User reportsvc exists and agent.conf contains MODE=production and PORT=18060"
chk2_det=""

chk3_pass=false
chk3_desc="report-agent.service is enabled and active under systemd"
chk3_det=""

chk4_pass=false
chk4_desc="Idempotency: second playbook run exits 0 with changed=0 and failed=0"
chk4_det=""

# Check 1: Syntax check
syntax_ok=false
syntax_out=$(ansible-playbook -i /srv/ansible-lab/inventory.ini --syntax-check /srv/ansible-lab/site.yml 2>&1) && syntax_ok=true

if [ "$syntax_ok" = true ]; then
    chk1_pass=true
    chk1_det="Playbook syntax check passed."
else
    safe_syntax=$(printf '%s' "$syntax_out" | head -n 3 | tr '\r\n"\\' ' ' | head -c 160)
    chk1_det="Syntax check failed: ${safe_syntax}"
fi

# Check 2: User and config
user_exists=false
has_mode=false
has_port=false

id reportsvc >/dev/null 2>&1 && user_exists=true
if [ -f /etc/report-agent/agent.conf ]; then
    grep -qE '^MODE=production[[:space:]]*$' /etc/report-agent/agent.conf 2>/dev/null && has_mode=true
    grep -qE '^PORT=18060[[:space:]]*$' /etc/report-agent/agent.conf 2>/dev/null && has_port=true
fi

if [ "$user_exists" = true ] && [ "$has_mode" = true ] && [ "$has_port" = true ]; then
    chk2_pass=true
    chk2_det="User reportsvc exists, agent.conf has MODE=production and PORT=18060."
else
    chk2_det="user_exists=${user_exists}, has_mode=${has_mode}, has_port=${has_port}"
fi

# Check 3: Service status
svc_enabled=false
svc_active=false

systemctl is-enabled report-agent.service >/dev/null 2>&1 && svc_enabled=true
systemctl is-active report-agent.service >/dev/null 2>&1 && svc_active=true

if [ "$svc_enabled" = true ] && [ "$svc_active" = true ]; then
    chk3_pass=true
    chk3_det="report-agent.service is enabled and active."
else
    chk3_det="enabled=${svc_enabled}, active=${svc_active}"
fi

# Check 4: Idempotency check
idempotent_ok=false
idemp_output=$(ansible-playbook -i /srv/ansible-lab/inventory.ini /srv/ansible-lab/site.yml 2>&1)
idemp_rc=$?

if [ "$idemp_rc" -eq 0 ]; then
    changed_count=$(echo "$idemp_output" | grep -oP 'changed=\K[0-9]+' | tail -1)
    failed_count=$(echo "$idemp_output" | grep -oP 'failed=\K[0-9]+' | tail -1)
    if [ "${changed_count:-1}" = "0" ] && [ "${failed_count:-1}" = "0" ]; then
        idempotent_ok=true
    fi
fi

if [ "$idempotent_ok" = true ]; then
    chk4_pass=true
    chk4_det="Idempotency confirmed: changed=0, failed=0 on second run."
else
    chk4_det="rc=${idemp_rc}, changed=${changed_count:-unknown}, failed=${failed_count:-unknown}"
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
  "lab_id": "lab-13",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-syntax-check",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-user-config",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-service-status",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-idempotency",
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
