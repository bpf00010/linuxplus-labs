#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="/usr/local/bin/metrics-watchdog.sh exists, is executable, and passes syntax check"
chk1_det=""

chk2_pass=false
chk2_desc="metrics-watchdog.timer is enabled, active, and has companion service"
chk2_det=""

chk3_pass=false
chk3_desc="Watchdog script successfully recovers stopped metrics-collector service"
chk3_det=""

watchdog_script="/usr/local/bin/metrics-watchdog.sh"

# Check 1: Script existence, executable bit, and syntax
script_exists=false
script_exec=false
script_syntax=false

if [ -f "$watchdog_script" ]; then
    script_exists=true
    if [ -x "$watchdog_script" ]; then
        script_exec=true
    fi
    if bash -n "$watchdog_script" >/dev/null 2>&1; then
        script_syntax=true
    fi
fi

if [ "$script_exists" = true ] && [ "$script_exec" = true ] && [ "$script_syntax" = true ]; then
    chk1_pass=true
    chk1_det="Watchdog script is executable and syntactically valid."
else
    chk1_det="exists=${script_exists}, exec=${script_exec}, syntax=${script_syntax}"
fi

# Check 2: metrics-watchdog.timer status
timer_enabled=false
timer_active=false
service_file_exists=false

if systemctl is-enabled metrics-watchdog.timer >/dev/null 2>&1; then
    timer_enabled=true
fi
if systemctl is-active metrics-watchdog.timer >/dev/null 2>&1; then
    timer_active=true
fi
if [ -f "/etc/systemd/system/metrics-watchdog.service" ] || [ -f "/lib/systemd/system/metrics-watchdog.service" ]; then
    service_file_exists=true
fi

if [ "$timer_enabled" = true ] && [ "$timer_active" = true ] && [ "$service_file_exists" = true ]; then
    chk2_pass=true
    chk2_det="metrics-watchdog.timer is enabled and active with companion service unit."
else
    chk2_det="timer_enabled=${timer_enabled}, timer_active=${timer_active}, companion_service=${service_file_exists}"
fi

# Check 3: Functional recovery test
# Stop metrics-collector, execute watchdog directly, verify recovery
recovery_success=false

systemctl stop metrics-collector.service >/dev/null 2>&1 || true

if [ "$chk1_pass" = true ]; then
    # Run the watchdog script
    "$watchdog_script" >/dev/null 2>&1 || true
    sleep 1

    if systemctl is-active metrics-collector.service >/dev/null 2>&1; then
        recovery_success=true
    fi
fi

# Ensure service remains started at the end of verify
systemctl start metrics-collector.service >/dev/null 2>&1 || true

if [ "$recovery_success" = true ]; then
    chk3_pass=true
    chk3_det="Watchdog script successfully detects stopped service and restores it to active."
else
    chk3_det="Watchdog failed to recover stopped metrics-collector service."
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
  "lab_id": "lab-04",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": ${score_total},
  "checks": [
    {
      "id": "chk-script",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-timer",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-recovery",
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
