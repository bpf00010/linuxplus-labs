#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="Does /srv/data/active_users.txt list unique sorted active usernames?"
chk1_det=""

chk2_pass=false
chk2_desc="Does /srv/data/app.conf replace old-db.internal with prod-db.internal?"
chk2_det=""

chk3_pass=false
chk3_desc="Are *.tmp files over 1MB deleted in /srv/data/files/ while keeping .log and small .tmp files?"
chk3_det=""

chk4_pass=false
chk4_desc="Does /usr/local/bin/check-file.sh print EXISTS (exit 0) or MISSING (exit 1)?"
chk4_det=""

# Check 1: active_users.txt
if [ -f /srv/data/active_users.txt ]; then
    expected=$(awk -F, 'NR>1 && $3=="active" {print $1}' /srv/data/users.csv | LC_ALL=C sort -u)
    actual=$(tr -d '\r' < /srv/data/active_users.txt | sed '/^[[:space:]]*$/d')
    if [ "$actual" = "$expected" ]; then
        chk1_pass=true
        chk1_det="/srv/data/active_users.txt matches expected sorted active users."
    else
        chk1_det="Content does not match unique sorted active usernames from users.csv."
    fi
else
    chk1_det="/srv/data/active_users.txt is missing."
fi

# Check 2: app.conf replacement
if [ -f /srv/data/app.conf ]; then
    old_cnt=$(grep -c 'old-db\.internal' /srv/data/app.conf || true)
    new_cnt=$(grep -c 'prod-db\.internal' /srv/data/app.conf || true)
    if [ "$old_cnt" -eq 0 ] && [ "$new_cnt" -ge 3 ]; then
        chk2_pass=true
        chk2_det="All old-db.internal entries replaced with prod-db.internal."
    else
        chk2_det="old_count=${old_cnt}, prod_count=${new_cnt}"
    fi
else
    chk2_det="/srv/data/app.conf is missing."
fi

# Check 3: find/delete large .tmp files only
big_tmp=$(find /srv/data/files -type f -name '*.tmp' -size +1M 2>/dev/null | wc -l)
kept_ok=false
if [ -f /srv/data/files/small1.tmp ] && [ -f /srv/data/files/sub/small2.tmp ] && \
   [ -f /srv/data/files/app.log ] && [ -f /srv/data/files/sub/access.log ]; then
    kept_ok=true
fi

if [ "$big_tmp" -eq 0 ] && [ "$kept_ok" = true ]; then
    chk3_pass=true
    chk3_det="Large .tmp files deleted; .log and small .tmp files intact."
else
    chk3_det="big_tmp_remaining=${big_tmp}, kept_files_intact=${kept_ok}"
fi

# Check 4: check-file.sh behavior
script="/usr/local/bin/check-file.sh"
if [ -f "$script" ] && [ -x "$script" ] && bash -n "$script" >/dev/null 2>&1; then
    out_ok=$("$script" /etc/hosts 2>/dev/null || true)
    rc_ok=0
    "$script" /etc/hosts >/dev/null 2>&1 || rc_ok=$?

    out_miss=$("$script" /var/tmp/nonexistent-lplab-check-999 2>/dev/null || true)
    rc_miss=0
    "$script" /var/tmp/nonexistent-lplab-check-999 >/dev/null 2>&1 || rc_miss=$?

    if [ "$out_ok" = "EXISTS" ] && [ "$rc_ok" -eq 0 ] && [ "$out_miss" = "MISSING" ] && [ "$rc_miss" -eq 1 ]; then
        chk4_pass=true
        chk4_det="check-file.sh returned EXISTS/0 and MISSING/1."
    else
        chk4_det="exists=(${out_ok},${rc_ok}), missing=(${out_miss},${rc_miss})"
    fi
else
    chk4_det="${script} missing, not executable, or failed bash -n."
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
  "lab_id": "lab-18",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-active-users",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-app-conf",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-find-delete",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-bash-script",
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
