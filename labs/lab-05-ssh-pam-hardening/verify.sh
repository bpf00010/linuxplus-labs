#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="sshd -T reports permitrootlogin no, passwordauthentication no, and allowgroups sshusers"
chk1_det=""

chk2_pass=false
chk2_desc="opsadmin is a member of group sshusers"
chk2_det=""

chk3_pass=false
chk3_desc="/home/opsadmin/.ssh is 700 and authorized_keys is 600 owned by opsadmin"
chk3_det=""

chk4_pass=false
chk4_desc="chage -l opsadmin enforces maximum password age of <= 90 days"
chk4_det=""

# Check 1: OpenSSH configuration syntax and effective settings
syntax_ok=false
root_login_no=false
pw_auth_no=false
allowgroups_ok=false

if sshd -t >/dev/null 2>&1; then
    syntax_ok=true
    sshd_dump=$(sshd -T 2>/dev/null || echo "")

    if echo "$sshd_dump" | grep -qi "^permitrootlogin no"; then
        root_login_no=true
    fi
    if echo "$sshd_dump" | grep -qi "^passwordauthentication no"; then
        pw_auth_no=true
    fi
    if echo "$sshd_dump" | grep -qi "^allowgroups.*sshusers"; then
        allowgroups_ok=true
    fi
fi

if [ "$syntax_ok" = true ] && [ "$root_login_no" = true ] && [ "$pw_auth_no" = true ] && [ "$allowgroups_ok" = true ]; then
    chk1_pass=true
    chk1_det="sshd configuration syntax is valid and security directives are enforced."
else
    chk1_det="syntax=${syntax_ok}, permitrootlogin_no=${root_login_no}, pwauth_no=${pw_auth_no}, allowgroups=${allowgroups_ok}"
fi

# Check 2: opsadmin group membership
if id -nG opsadmin 2>/dev/null | grep -qw "sshusers"; then
    chk2_pass=true
    chk2_det="opsadmin is confirmed member of group sshusers."
else
    chk2_det="opsadmin groups: $(id -nG opsadmin 2>/dev/null || echo 'user not found')"
fi

# Check 3: File permissions and ownership on ~/.ssh
ssh_dir="/home/opsadmin/.ssh"
auth_keys="/home/opsadmin/.ssh/authorized_keys"

dir_perm_ok=false
dir_owner_ok=false
file_perm_ok=false
file_owner_ok=false

if [ -d "$ssh_dir" ]; then
    [ "$(stat -c "%a" "$ssh_dir" 2>/dev/null)" = "700" ] && dir_perm_ok=true
    [ "$(stat -c "%U" "$ssh_dir" 2>/dev/null)" = "opsadmin" ] && dir_owner_ok=true
fi

if [ -f "$auth_keys" ]; then
    [ "$(stat -c "%a" "$auth_keys" 2>/dev/null)" = "600" ] && file_perm_ok=true
    [ "$(stat -c "%U" "$auth_keys" 2>/dev/null)" = "opsadmin" ] && file_owner_ok=true
fi

if [ "$dir_perm_ok" = true ] && [ "$dir_owner_ok" = true ] && [ "$file_perm_ok" = true ] && [ "$file_owner_ok" = true ]; then
    chk3_pass=true
    chk3_det="SSH directory and authorized_keys have strict permissions (700/600) and correct ownership."
else
    chk3_det="dir_perm=${dir_perm_ok}, dir_owner=${dir_owner_ok}, file_perm=${file_perm_ok}, file_owner=${file_owner_ok}"
fi

# Check 4: Password aging via chage
max_days=$(chage -l opsadmin 2>/dev/null | grep -i "Maximum number of days between password change" | awk -F: '{print $2}' | tr -d ' ' || echo "99999")

if [ -n "$max_days" ] && [ "$max_days" -gt 0 ] && [ "$max_days" -le 90 ]; then
    chk4_pass=true
    chk4_det="opsadmin maximum password age is set to ${max_days} days."
else
    chk4_det="opsadmin maximum password age is ${max_days} (expected <= 90 and > 0)"
fi

# Calculate score
score_passed=0
[ "$chk1_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk2_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk3_pass" = true ] && score_passed=$((score_passed + 1))
[ "$chk4_pass" = true ] && score_passed=$((score_passed + 1))
score_total=4

overall_passed=false
[ "$score_passed" -eq "$score_total" ] && overall_passed=true

# Output strict JSON
cat <<EOF
{
  "lab_id": "lab-05",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": ${score_total},
  "checks": [
    {
      "id": "chk-sshd-config",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-group",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-ssh-perms",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-chage",
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
