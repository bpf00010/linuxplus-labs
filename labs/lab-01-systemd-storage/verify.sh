#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="Is /mnt/appdata mounted from /var/lib/lplab/appdata.img and listed in /etc/fstab?"
chk1_det=""

chk2_pass=false
chk2_desc="Is app-worker.service unmasked, enabled, and active?"
chk2_det=""

chk3_pass=false
chk3_desc="Is /var/log/app-worker/debug.log <= 5MB and does /etc/logrotate.d/app-worker exist?"
chk3_det=""

# Check 1: Mount & fstab
is_mounted=false
if mountpoint -q /mnt/appdata 2>/dev/null; then
    is_mounted=true
fi

fstab_valid=false
if grep -E "^/var/lib/lplab/appdata\.img\s+/mnt/appdata\s+ext4" /etc/fstab >/dev/null 2>&1; then
    fstab_valid=true
fi

if [ "$is_mounted" = true ] && [ "$fstab_valid" = true ]; then
    chk1_pass=true
    chk1_det="/mnt/appdata mounted and /etc/fstab entry valid."
else
    chk1_det="mounted=${is_mounted}, valid_fstab=${fstab_valid}"
fi

# Check 2: Service status
svc_masked=true
if [ "$(systemctl is-enabled app-worker.service 2>/dev/null || true)" != "masked" ]; then
    svc_masked=false
fi

svc_enabled=false
if systemctl is-enabled app-worker.service >/dev/null 2>&1; then
    svc_enabled=true
fi

svc_active=false
if systemctl is-active app-worker.service >/dev/null 2>&1; then
    svc_active=true
fi

if [ "$svc_masked" = false ] && [ "$svc_enabled" = true ] && [ "$svc_active" = true ]; then
    chk2_pass=true
    chk2_det="app-worker.service is unmasked, enabled, and active."
else
    chk2_det="masked=${svc_masked}, enabled=${svc_enabled}, active=${svc_active}"
fi

# Check 3: Log file size & logrotate config
log_ok=false
log_path="/var/log/app-worker/debug.log"
if [ -f "$log_path" ]; then
    size_bytes=$(stat -c%s "$log_path" 2>/dev/null || echo 99999999)
    if [ "$size_bytes" -le 5242880 ]; then
        log_ok=true
    fi
else
    log_ok=true
fi

rotate_cfg_ok=false
if [ -f "/etc/logrotate.d/app-worker" ]; then
    rotate_cfg_ok=true
fi

if [ "$log_ok" = true ] && [ "$rotate_cfg_ok" = true ]; then
    chk3_pass=true
    chk3_det="debug.log <= 5MB and /etc/logrotate.d/app-worker exists."
else
    chk3_det="under_5MB=${log_ok}, logrotate_cfg=${rotate_cfg_ok}"
fi

score_passed=0
[ "$chk1_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk2_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk3_pass" = true ] && score_passed=$((score_passed + 1))
score_total=3

overall_passed=false
[ "$score_passed" -eq "$score_total" ] && overall_passed=true

cat <<EOF
{
  "lab_id": "lab-01",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": ${score_total},
  "checks": [
    {
      "id": "chk-mount",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-service",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-logrotate",
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
