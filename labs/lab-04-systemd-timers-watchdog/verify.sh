#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="/usr/local/bin/metrics-watchdog.sh exists, is executable, and passes syntax check"
chk1_det=""

chk2_pass=false
chk2_desc="metrics-watchdog.timer is enabled and active, and companion service exists"
chk2_det=""

chk3_pass=false
chk3_desc="Legacy cron job /etc/cron.d/metrics-watchdog has been removed"
chk3_det=""

chk4_pass=false
chk4_desc="Functional recovery: watchdog brings stopped metrics-collector.service back to active"
chk4_det=""

script_path="/usr/local/bin/metrics-watchdog.sh"

# Check 1: Script existence, executable, syntax
if [ -f "$script_path" ] && [ -x "$script_path" ]; then
    if bash -n "$script_path" >/dev/null 2>&1; then
        chk1_pass=true
        chk1_det="Watchdog script exists, has execute permissions, and passed bash -n."
    else
        chk1_det="Watchdog script exists but contains syntax errors."
    fi
else
    chk1_det="Watchdog script missing or lacks execute permissions at ${script_path}."
fi

# Check 2: Timer and service units
timer_enabled=false
timer_active=false
service_exists=false

if systemctl is-enabled metrics-watchdog.timer >/dev/null 2>&1; then
    timer_enabled=true
fi

if systemctl is-active metrics-watchdog.timer >/dev/null 2>&1; then
    timer_active=true
fi

if [ -f /etc/systemd/system/metrics-watchdog.service ]; then
    service_exists=true
fi

if [ "$timer_enabled" = true ] && [ "$timer_active" = true ] && [ "$service_exists" = true ]; then
    chk2_pass=true
    chk2_det="metrics-watchdog.timer is enabled and active with companion service in place."
else
    chk2_det="Timer status: enabled=${timer_enabled}, active=${timer_active}, service_file=${service_exists}"
fi

# Check 3: Cron job decommissioned
if [ ! -f /etc/cron.d/metrics-watchdog ]; then
    chk3_pass=true
    chk3_det="Legacy /etc/cron.d/metrics-watchdog cron job has been removed."
else
    chk3_det="Legacy /etc/cron.d/metrics-watchdog still exists."
fi

# Check 4: Functional test of watchdog script
if [ -x "$script_path" ]; then
    # Stop collector and run watchdog
    systemctl stop metrics-collector.service >/dev/null 2>&1 || true
    "$script_path" >/dev/null 2>&1 || true

    collector_active=false
    collector_enabled=false

    if systemctl is-active metrics-collector.service >/dev/null 2>&1; then
        collector_active=true
    fi
    if systemctl is-enabled metrics-collector.service >/dev/null 2>&1; then
        collector_enabled=true
    fi

    if [ "$collector_active" = true ] && [ "$collector_enabled" = true ]; then
        chk4_pass=true
        chk4_det="Watchdog successfully restored metrics-collector.service to active and enabled state."
    else
        chk4_det="After running watchdog: active=${collector_active}, enabled=${collector_enabled}"
    fi
else
    chk4_det="Cannot run functional test because ${script_path} is missing or not executable."
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
  "lab_id": "lab-04",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-watchdog-script",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-timer-status",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-cron-removed",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-functional-recovery",
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
