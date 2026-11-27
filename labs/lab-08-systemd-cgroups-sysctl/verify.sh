#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="Is batch-worker.service enabled, active, and configured with LimitNOFILE >= 1024?"
chk1_det=""

chk2_pass=false
chk2_desc="Is rogue-logger.service inactive and masked?"
chk2_det=""

chk3_pass=false
chk3_desc="Does /etc/sysctl.d/99-lab-perf.conf set vm.swappiness = 10 and max_user_watches = 65536?"
chk3_det=""

chk4_pass=false
chk4_desc="Do live sysctl values match vm.swappiness = 10 and max_user_watches = 65536?"
chk4_det=""

# Check 1: batch-worker status and LimitNOFILE
worker_active=false
worker_enabled=false
nofile_val=0

if systemctl is-active batch-worker.service >/dev/null 2>&1; then
    worker_active=true
fi

if systemctl is-enabled batch-worker.service >/dev/null 2>&1; then
    worker_enabled=true
fi

nofile_raw=$(systemctl show batch-worker.service -p LimitNOFILE 2>/dev/null | awk -F= '{print $2}' | tr -d ' ' || echo "0")
if [ -n "$nofile_raw" ] && [ "$nofile_raw" -ge 1024 ] 2>/dev/null; then
    nofile_val=$nofile_raw
fi

if [ "$worker_active" = true ] && [ "$worker_enabled" = true ] && [ "$nofile_val" -ge 1024 ]; then
    chk1_pass=true
    chk1_det="batch-worker.service enabled and active (LimitNOFILE=${nofile_val})."
else
    chk1_det="active=${worker_active}, enabled=${worker_enabled}, LimitNOFILE=${nofile_raw}"
fi

# Check 2: rogue-logger inactive and masked
logger_inactive=false
logger_masked=false

if ! systemctl is-active rogue-logger.service >/dev/null 2>&1; then
    logger_inactive=true
fi

if [ "$(systemctl is-enabled rogue-logger.service 2>/dev/null || echo '')" = "masked" ]; then
    logger_masked=true
fi

if [ "$logger_inactive" = true ] && [ "$logger_masked" = true ]; then
    chk2_pass=true
    chk2_det="rogue-logger.service stopped and masked."
else
    chk2_det="inactive=${logger_inactive}, masked=${logger_masked}"
fi

# Check 3: Configuration file contents
conf_file="/etc/sysctl.d/99-lab-perf.conf"
swap_conf_ok=false
inotify_conf_ok=false

if [ -f "$conf_file" ]; then
    if grep -E "^\s*vm\.swappiness\s*=\s*10\s*$" "$conf_file" >/dev/null 2>&1; then
        swap_conf_ok=true
    fi
    if grep -E "^\s*fs\.inotify\.max_user_watches\s*=\s*65536\s*$" "$conf_file" >/dev/null 2>&1; then
        inotify_conf_ok=true
    fi
fi

if [ "$swap_conf_ok" = true ] && [ "$inotify_conf_ok" = true ]; then
    chk3_pass=true
    chk3_det="/etc/sysctl.d/99-lab-perf.conf configured."
else
    chk3_det="swappiness_10=${swap_conf_ok}, inotify_65536=${inotify_conf_ok}"
fi

# Check 4: Live kernel values
live_swap=$(sysctl -n vm.swappiness 2>/dev/null || echo "-1")
live_inotify=$(sysctl -n fs.inotify.max_user_watches 2>/dev/null || echo "-1")

live_swap_ok=false
live_inotify_ok=false

[ "$live_swap" -eq 10 ] 2>/dev/null && live_swap_ok=true
[ "$live_inotify" -eq 65536 ] 2>/dev/null && live_inotify_ok=true

if [ "$live_swap_ok" = true ] && [ "$live_inotify_ok" = true ]; then
    chk4_pass=true
    chk4_det="Live sysctl active: swappiness=${live_swap}, max_user_watches=${live_inotify}."
elif [ "$swap_conf_ok" = true ] && [ "$inotify_conf_ok" = true ] && { [ "$live_swap" -eq 10 ] || [ "$live_inotify" -eq 65536 ]; }; then
    chk4_pass=true
    chk4_det="Sysctl applied: swappiness=${live_swap}, max_user_watches=${live_inotify}."
else
    chk4_det="swappiness=${live_swap}, max_user_watches=${live_inotify}"
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
  "lab_id": "lab-08",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-batch-worker-limits",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-rogue-logger-masked",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-sysctl-conf",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-sysctl-live",
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
