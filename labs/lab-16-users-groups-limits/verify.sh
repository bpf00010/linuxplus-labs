#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="Do /etc/skel/WELCOME.txt and /etc/skel/bin exist?"
chk1_det=""

chk2_pass=false
chk2_desc="Do group ops and user appuser exist with /bin/bash and skel files in /home/appuser?"
chk2_det=""

chk3_pass=false
chk3_desc="Is formeremp locked, set to /usr/sbin/nologin, and expired?"
chk3_det=""

chk4_pass=false
chk4_desc="Does /etc/security/limits.d/99-appuser.conf set soft nofile 4096 and hard nofile 8192?"
chk4_det=""

# Check 1: /etc/skel
if [ -f /etc/skel/WELCOME.txt ] && [ -d /etc/skel/bin ]; then
    chk1_pass=true
    chk1_det="/etc/skel/WELCOME.txt and /etc/skel/bin exist."
else
    chk1_det="Missing /etc/skel/WELCOME.txt or /etc/skel/bin."
fi

# Check 2: group ops and user appuser
grp_ok=false
usr_ok=false
shell_ok=false
in_ops=false
skel_copied=false

getent group ops >/dev/null 2>&1 && grp_ok=true
if id appuser >/dev/null 2>&1; then
    usr_ok=true
    usr_shell=$(getent passwd appuser | cut -d: -f7)
    [ "$usr_shell" = "/bin/bash" ] && shell_ok=true
    id -Gn appuser 2>/dev/null | grep -qw "ops" && in_ops=true
    [ -f /home/appuser/WELCOME.txt ] && [ -d /home/appuser/bin ] && skel_copied=true
fi

if [ "$grp_ok" = true ] && [ "$usr_ok" = true ] && [ "$shell_ok" = true ] && [ "$in_ops" = true ] && [ "$skel_copied" = true ]; then
    chk2_pass=true
    chk2_det="ops and appuser configured with /etc/skel files."
else
    chk2_det="grp=${grp_ok}, user=${usr_ok}, bash=${shell_ok}, in_ops=${in_ops}, skel=${skel_copied}"
fi

# Check 3: formeremp locked, nologin, expired
locked=false
nologin=false
expired=false

if id formeremp >/dev/null 2>&1; then
    f_shell=$(getent passwd formeremp | cut -d: -f7)
    if [ "$f_shell" = "/usr/sbin/nologin" ] || [ "$f_shell" = "/sbin/nologin" ]; then
        nologin=true
    fi
    pw_status=$(passwd -S formeremp 2>/dev/null | awk '{print $2}' || echo "")
    if [ "$pw_status" = "L" ] || [ "$pw_status" = "LK" ]; then
        locked=true
    fi
    exp_days=$(awk -F: '$1=="formeremp"{print $8}' /etc/shadow 2>/dev/null || echo "")
    today_days=$(($(date +%s) / 86400))
    if [ -n "$exp_days" ] && [ "$exp_days" -le "$today_days" ] 2>/dev/null; then
        expired=true
    fi
fi

if [ "$locked" = true ] && [ "$nologin" = true ] && [ "$expired" = true ]; then
    chk3_pass=true
    chk3_det="formeremp is locked, nologin, and expired."
else
    chk3_det="locked=${locked}, nologin=${nologin}, expired=${expired}"
fi

# Check 4: limits.d file
limits_file="/etc/security/limits.d/99-appuser.conf"
soft_ok=false
hard_ok=false

if [ -f "$limits_file" ]; then
    grep -qE '^[[:space:]]*appuser[[:space:]]+soft[[:space:]]+nofile[[:space:]]+4096([[:space:]]|$)' "$limits_file" && soft_ok=true
    grep -qE '^[[:space:]]*appuser[[:space:]]+hard[[:space:]]+nofile[[:space:]]+8192([[:space:]]|$)' "$limits_file" && hard_ok=true
fi

if [ "$soft_ok" = true ] && [ "$hard_ok" = true ]; then
    chk4_pass=true
    chk4_det="99-appuser.conf sets soft 4096 and hard 8192."
else
    chk4_det="soft_4096=${soft_ok}, hard_8192=${hard_ok}"
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
  "lab_id": "lab-16",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-skel",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-appuser",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-formeremp-locked",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-limits",
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
