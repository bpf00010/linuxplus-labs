#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="sshd -t passes and sshd -T reports permitrootlogin no, passwordauthentication no, and allowgroups sshusers"
chk1_det=""

chk2_pass=false
chk2_desc="SSH daemon (ssh.service or ssh.socket) is active under systemd"
chk2_det=""

chk3_pass=false
chk3_desc="opsadmin is in group sshusers, and .ssh directory (700) and authorized_keys (600) have secure permissions"
chk3_det=""

chk4_pass=false
chk4_desc="chage -l opsadmin reports maximum password age between 1 and 90 days"
chk4_det=""

# Check 1: OpenSSH configuration and effective directives
syntax_ok=false
root_no=false
pass_no=false
allow_ok=false

if /usr/sbin/sshd -t >/dev/null 2>&1; then
    syntax_ok=true
    sshd_out=$(/usr/sbin/sshd -T 2>/dev/null || echo "")

    if echo "$sshd_out" | grep -Ei "^permitrootlogin\s+no" >/dev/null 2>&1; then
        root_no=true
    fi
    if echo "$sshd_out" | grep -Ei "^passwordauthentication\s+no" >/dev/null 2>&1; then
        pass_no=true
    fi
    if echo "$sshd_out" | grep -Ei "^allowgroups\s+.*sshusers" >/dev/null 2>&1; then
        allow_ok=true
    fi
fi

if [ "$syntax_ok" = true ] && [ "$root_no" = true ] && [ "$pass_no" = true ] && [ "$allow_ok" = true ]; then
    chk1_pass=true
    chk1_det="sshd -t syntax is valid and effective config enforces root=no, password=no, allowgroups=sshusers."
else
    chk1_det="syntax=${syntax_ok}, permitrootlogin_no=${root_no}, passwordauth_no=${pass_no}, allowgroups_sshusers=${allow_ok}"
fi

# Check 2: SSH systemd unit active
ssh_active=false
if systemctl is-active ssh >/dev/null 2>&1 || systemctl is-active ssh.socket >/dev/null 2>&1; then
    ssh_active=true
fi

if [ "$ssh_active" = true ]; then
    chk2_pass=true
    chk2_det="SSH daemon or socket is actively running under systemd."
else
    chk2_det="Neither ssh.service nor ssh.socket is currently active."
fi

# Check 3: opsadmin group and file permissions
in_group=false
dir_owner=""
dir_mode=""
key_owner=""
key_mode=""

if id -Gn opsadmin 2>/dev/null | grep -qw "sshusers"; then
    in_group=true
fi

ssh_dir="/home/opsadmin/.ssh"
key_file="/home/opsadmin/.ssh/authorized_keys"

if [ -d "$ssh_dir" ]; then
    dir_owner=$(stat -c "%U:%G" "$ssh_dir" 2>/dev/null || echo "")
    dir_mode=$(stat -c "%a" "$ssh_dir" 2>/dev/null || echo "")
fi

if [ -f "$key_file" ]; then
    key_owner=$(stat -c "%U:%G" "$key_file" 2>/dev/null || echo "")
    key_mode=$(stat -c "%a" "$key_file" 2>/dev/null || echo "")
fi

if [ "$in_group" = true ] && [ "$dir_owner" = "opsadmin:opsadmin" ] && [ "$dir_mode" = "700" ] && \
   [ "$key_owner" = "opsadmin:opsadmin" ] && [ "$key_mode" = "600" ]; then
    chk3_pass=true
    chk3_det="opsadmin is member of sshusers, .ssh is 0700 opsadmin, authorized_keys is 0600 opsadmin."
else
    chk3_det="in_group=${in_group}, dir=${dir_owner}(${dir_mode}), keys=${key_owner}(${key_mode})"
fi

# Check 4: Password aging via chage
max_days=$(chage -l opsadmin 2>/dev/null | grep -i "Maximum number of days" | awk -F: '{print $2}' | tr -d ' ' || echo "-1")

if [ -n "$max_days" ] && [ "$max_days" -ge 1 ] 2>/dev/null && [ "$max_days" -le 90 ] 2>/dev/null; then
    chk4_pass=true
    chk4_det="Maximum password age for opsadmin is compliant: ${max_days} days (policy <= 90)."
else
    chk4_det="Maximum password age for opsadmin is ${max_days} (expected between 1 and 90)."
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
  "lab_id": "lab-07",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-sshd-config",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-ssh-service",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-user-ssh-perms",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-chage-policy",
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
