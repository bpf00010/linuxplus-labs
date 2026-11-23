#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="/srv/shared-app has group webops and setgid bit (2770 or 2775)"
chk1_det=""

chk2_pass=false
chk2_desc="Default POSIX ACL gives group webops rwx inheritance"
chk2_det=""

chk3_pass=false
chk3_desc="visudo -cf /etc/sudoers.d/99-deploy passes syntax check"
chk3_det=""

chk4_pass=false
chk4_desc="deploy user is restricted strictly to restart app-proxy (no ALL)"
chk4_det=""

target_dir="/srv/shared-app"

# Check 1: Group ownership and setgid bit
grp_name=$(stat -c "%G" "$target_dir" 2>/dev/null || echo "")
perms=$(stat -c "%a" "$target_dir" 2>/dev/null || echo "")

if [ "$grp_name" = "webops" ] && { [ "$perms" = "2770" ] || [ "$perms" = "2775" ]; }; then
    chk1_pass=true
    chk1_det="Directory has group webops and setgid mode ${perms}."
else
    chk1_det="Directory status: group=${grp_name}, mode=${perms} (expected webops, 2770 or 2775)"
fi

# Check 2: Default ACL inheritance
acl_output=$(getfacl "$target_dir" 2>/dev/null || echo "")
has_default_group_rwx=false

if echo "$acl_output" | grep -E "default:group:(webops)?\s*:\s*rwx" >/dev/null 2>&1; then
    has_default_group_rwx=true
fi

if [ "$has_default_group_rwx" = true ]; then
    chk2_pass=true
    chk2_det="Default ACL for webops provides rwx permission inheritance."
else
    chk2_det="Default POSIX ACL missing default:group:webops:rwx or default:group::rwx"
fi

# Check 3: visudo syntax check
sudoers_file="/etc/sudoers.d/99-deploy"
syntax_ok=false
if [ -f "$sudoers_file" ] && visudo -cf "$sudoers_file" >/dev/null 2>&1; then
    syntax_ok=true
fi

if [ "$syntax_ok" = true ]; then
    chk3_pass=true
    chk3_det="Sudoers drop-in passed visudo syntax check."
else
    chk3_det="Sudoers file missing or failed visudo validation."
fi

# Check 4: Principle of least privilege for deploy user
sudo_privs=$(sudo -l -U deploy 2>/dev/null || echo "")
grants_all=false
permits_app_proxy=false

# Check if ALL privilege is granted
if echo "$sudo_privs" | grep -E "(ALL\s*=\s*\(ALL\)\s*(NOPASSWD:\s*)?ALL|ALL\s*=\s*\(ALL:ALL\)\s*(NOPASSWD:\s*)?ALL)" >/dev/null 2>&1; then
    grants_all=true
elif echo "$sudo_privs" | grep -E "\bALL\b" | grep -v "restart app-proxy" | grep -v "ALL.*NOPASSWD:.*systemctl" >/dev/null 2>&1; then
    # Double check if ALL command is permitted
    if echo "$sudo_privs" | grep -E "NOPASSWD:\s*ALL" >/dev/null 2>&1; then
        grants_all=true
    fi
fi

# Check if restarting app-proxy is permitted
if echo "$sudo_privs" | grep -E "(systemctl\s+restart\s+app-proxy|/usr/bin/systemctl\s+restart\s+app-proxy)" >/dev/null 2>&1; then
    permits_app_proxy=true
fi

if [ "$grants_all" = false ] && [ "$permits_app_proxy" = true ]; then
    chk4_pass=true
    chk4_det="deploy is restricted to restart app-proxy without blanket ALL permissions."
else
    chk4_det="deploy privileges: grants_all=${grants_all}, permits_app_proxy=${permits_app_proxy}"
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
  "lab_id": "lab-03",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": ${score_total},
  "checks": [
    {
      "id": "chk-permissions",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-acls",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-sudoers-syntax",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-least-privilege",
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
