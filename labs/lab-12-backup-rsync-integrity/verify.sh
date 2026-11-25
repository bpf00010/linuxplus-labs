#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="bin/run.sh is executable, current.conf is a symlink to app.conf, and SHA256SUMS check passes"
chk1_det=""

chk2_pass=false
chk2_desc="backup-mirror contains app.conf and bin/run.sh with no .tmp files and no cache directory"
chk2_det=""

chk3_pass=false
chk3_desc="verified-mirror.tar.xz is a valid tar.xz archive containing app.conf"
chk3_det=""

chk4_pass=false
chk4_desc="verified-mirror.tar.xz.sha256 checksum verification passes"
chk4_det=""

# Check 1: Restored production files
run_exec=false
symlink_ok=false
checksum_ok=false

if [ -x /srv/app-prod/bin/run.sh ]; then
    run_exec=true
fi

if [ -L /srv/app-prod/current.conf ]; then
    link_target=$(readlink /srv/app-prod/current.conf 2>/dev/null || echo "")
    if [ "$link_target" = "app.conf" ]; then
        symlink_ok=true
    fi
fi

if (cd /srv/app-prod && sha256sum -c SHA256SUMS >/dev/null 2>&1); then
    checksum_ok=true
fi

if [ "$run_exec" = true ] && [ "$symlink_ok" = true ] && [ "$checksum_ok" = true ]; then
    chk1_pass=true
    chk1_det="bin/run.sh is executable, current.conf -> app.conf, SHA256SUMS passes."
else
    chk1_det="run_exec=${run_exec}, symlink_ok=${symlink_ok}, checksum_ok=${checksum_ok}"
fi

# Check 2: Backup mirror contents
mirror_appconf=false
mirror_runsh=false
no_tmp=true
no_cache=true

if [ -f /srv/backup-mirror/app.conf ] && cmp -s /srv/app-prod/app.conf /srv/backup-mirror/app.conf; then
    mirror_appconf=true
fi
if [ -f /srv/backup-mirror/bin/run.sh ] && cmp -s /srv/app-prod/bin/run.sh /srv/backup-mirror/bin/run.sh; then
    mirror_runsh=true
fi
tmp_count=$(find /srv/backup-mirror -name '*.tmp' 2>/dev/null | wc -l)
[ "$tmp_count" -gt 0 ] && no_tmp=false
[ -d /srv/backup-mirror/cache ] && no_cache=false

if [ "$mirror_appconf" = true ] && [ "$mirror_runsh" = true ] && [ "$no_tmp" = true ] && [ "$no_cache" = true ]; then
    chk2_pass=true
    chk2_det="backup-mirror has app.conf and bin/run.sh, no .tmp files, no cache directory."
else
    chk2_det="appconf=${mirror_appconf}, runsh=${mirror_runsh}, no_tmp=${no_tmp}, no_cache=${no_cache}"
fi

# Check 3: verified-mirror.tar.xz is valid and contains app.conf
archive_valid=false
contains_appconf=false

if [ -f /var/backups/verified-mirror.tar.xz ]; then
    if tar tJf /var/backups/verified-mirror.tar.xz >/dev/null 2>&1; then
        archive_valid=true
        if tar tJf /var/backups/verified-mirror.tar.xz 2>/dev/null | grep -q 'app.conf'; then
            contains_appconf=true
        fi
    fi
fi

if [ "$archive_valid" = true ] && [ "$contains_appconf" = true ]; then
    chk3_pass=true
    chk3_det="verified-mirror.tar.xz is valid and contains app.conf."
else
    chk3_det="archive_valid=${archive_valid}, contains_appconf=${contains_appconf}"
fi

# Check 4: SHA-256 checksum verification
checksum_file_ok=false
if [ -f /var/backups/verified-mirror.tar.xz.sha256 ]; then
    if (cd /var/backups && sha256sum -c verified-mirror.tar.xz.sha256 >/dev/null 2>&1); then
        checksum_file_ok=true
    fi
fi

if [ "$checksum_file_ok" = true ]; then
    chk4_pass=true
    chk4_det="SHA-256 checksum file verification passes."
else
    chk4_det="checksum_file_ok=${checksum_file_ok}"
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
  "lab_id": "lab-12",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-restore-integrity",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-mirror-contents",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-archive-valid",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-checksum-verify",
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
