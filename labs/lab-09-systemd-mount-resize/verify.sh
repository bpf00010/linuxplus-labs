#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="/mnt/archive is mounted as ext4 with nodev, nosuid, and noexec options"
chk1_det=""

chk2_pass=false
chk2_desc="Mounted filesystem size at /mnt/archive is at least 85MB"
chk2_det=""

chk3_pass=false
chk3_desc="mnt-archive.mount is enabled and active under systemd"
chk3_det=""

chk4_pass=false
chk4_desc="archive-sync.service is enabled and active under systemd"
chk4_det=""

# Check 1: Mount presence and options
mount_opts=$(findmnt -no OPTIONS /mnt/archive 2>/dev/null || echo "")
fstype=$(findmnt -no FSTYPE /mnt/archive 2>/dev/null || echo "")

has_nodev=false
has_nosuid=false
has_noexec=false

if echo "$mount_opts" | grep -qw "nodev"; then
    has_nodev=true
fi
if echo "$mount_opts" | grep -qw "nosuid"; then
    has_nosuid=true
fi
if echo "$mount_opts" | grep -qw "noexec"; then
    has_noexec=true
fi

if [ -n "$mount_opts" ] && [ "$fstype" = "ext4" ] && [ "$has_nodev" = true ] && [ "$has_nosuid" = true ] && [ "$has_noexec" = true ]; then
    chk1_pass=true
    chk1_det="/mnt/archive is mounted as ext4 with required options: ${mount_opts}."
else
    chk1_det="Mount status: fstype=${fstype}, options=${mount_opts} (requires ext4, nodev, nosuid, noexec)"
fi

# Check 2: Filesystem size >= 85MB
size_mb=$(df -BM --output=size /mnt/archive 2>/dev/null | tail -n 1 | tr -d ' M' || echo "0")

if [ -n "$size_mb" ] && [ "$size_mb" -ge 85 ] 2>/dev/null; then
    chk2_pass=true
    chk2_det="Mounted filesystem size is ${size_mb}MB (meets >= 85MB requirement)."
else
    chk2_det="Mounted filesystem size is ${size_mb}MB (expected >= 85MB)"
fi

# Check 3: mnt-archive.mount status
mount_enabled=false
mount_active=false

if systemctl is-enabled mnt-archive.mount >/dev/null 2>&1; then
    mount_enabled=true
fi

if systemctl is-active mnt-archive.mount >/dev/null 2>&1; then
    mount_active=true
fi

if [ "$mount_enabled" = true ] && [ "$mount_active" = true ]; then
    chk3_pass=true
    chk3_det="mnt-archive.mount is enabled and active."
else
    chk3_det="mnt-archive.mount status: enabled=${mount_enabled}, active=${mount_active}"
fi

# Check 4: archive-sync.service status
svc_enabled=false
svc_active=false

if systemctl is-enabled archive-sync.service >/dev/null 2>&1; then
    svc_enabled=true
fi

if systemctl is-active archive-sync.service >/dev/null 2>&1; then
    svc_active=true
fi

if [ "$svc_enabled" = true ] && [ "$svc_active" = true ]; then
    chk4_pass=true
    chk4_det="archive-sync.service is enabled and active."
else
    chk4_det="archive-sync.service status: enabled=${svc_enabled}, active=${svc_active}"
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
  "lab_id": "lab-09",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-mount-options",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-filesystem-size",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-mount-unit",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-archive-sync",
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
