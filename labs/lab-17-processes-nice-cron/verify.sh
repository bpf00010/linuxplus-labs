#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="Is cpu-hog.service stopped and disabled with no cpu-hog.sh process running?"
chk1_det=""

chk2_pass=false
chk2_desc="Is batch-job.service active with process niceness 15?"
chk2_det=""

chk3_pass=false
chk3_desc="Does /etc/cron.allow permit only root and sysadmin?"
chk3_det=""

chk4_pass=false
chk4_desc="Does sysadmin crontab run /usr/local/bin/heartbeat.sh every 5 minutes and is cron.service active?"
chk4_det=""

# Check 1: cpu-hog stopped, disabled, no process
hog_active=true
hog_enabled=true
hog_proc=true

! systemctl is-active cpu-hog.service >/dev/null 2>&1 && hog_active=false
! systemctl is-enabled cpu-hog.service >/dev/null 2>&1 && hog_enabled=false
! pgrep -f '/usr/local/bin/cpu-hog.sh' >/dev/null 2>&1 && hog_proc=false

if [ "$hog_active" = false ] && [ "$hog_enabled" = false ] && [ "$hog_proc" = false ]; then
    chk1_pass=true
    chk1_det="cpu-hog.service stopped, disabled, and no process running."
else
    chk1_det="active=${hog_active}, enabled=${hog_enabled}, proc=${hog_proc}"
fi

# Check 2: batch-job active with niceness 15
batch_active=false
batch_ni=""

if systemctl is-active batch-job.service >/dev/null 2>&1; then
    batch_active=true
    pid=$(systemctl show -p MainPID --value batch-job.service 2>/dev/null || echo "0")
    if [ -n "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null; then
        batch_ni=$(ps -o ni= -p "$pid" 2>/dev/null | tr -d ' ' || echo "")
    fi
fi

if [ "$batch_active" = true ] && [ "$batch_ni" = "15" ]; then
    chk2_pass=true
    chk2_det="batch-job.service running with niceness 15."
else
    chk2_det="active=${batch_active}, niceness=${batch_ni} (expected 15)"
fi

# Check 3: /etc/cron.allow has only root and sysadmin
allow_ok=false
if [ -f /etc/cron.allow ]; then
    has_root=false
    has_sysadmin=false
    extra_users=false
    grep -qx 'root' /etc/cron.allow && has_root=true
    grep -qx 'sysadmin' /etc/cron.allow && has_sysadmin=true
    other_lines=$(grep -vE '^(root|sysadmin|[[:space:]]*)$' /etc/cron.allow | wc -l)
    [ "$other_lines" -gt 0 ] && extra_users=true
    if [ "$has_root" = true ] && [ "$has_sysadmin" = true ] && [ "$extra_users" = false ]; then
        allow_ok=true
    fi
fi

if [ "$allow_ok" = true ]; then
    chk3_pass=true
    chk3_det="/etc/cron.allow allows only root and sysadmin."
else
    chk3_det="/etc/cron.allow missing or contains unexpected entries."
fi

# Check 4: cron.service active and sysadmin crontab entry
cron_active=false
crontab_ok=false

systemctl is-active cron.service >/dev/null 2>&1 && cron_active=true
if crontab -l -u sysadmin 2>/dev/null | grep -qE '^\*/5[[:space:]]+\*[[:space:]]+\*[[:space:]]+\*[[:space:]]+\*[[:space:]]+.*\/usr\/local\/bin\/heartbeat\.sh'; then
    crontab_ok=true
fi

if [ "$cron_active" = true ] && [ "$crontab_ok" = true ]; then
    chk4_pass=true
    chk4_det="cron.service active and sysadmin heartbeat job scheduled."
else
    chk4_det="cron_active=${cron_active}, crontab_ok=${crontab_ok}"
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
  "lab_id": "lab-17",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-cpu-hog-stopped",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-batch-job-nice",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-cron-allow",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-sysadmin-crontab",
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
