#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="Does apt-get check succeed without parse errors?"
chk1_det=""

chk2_pass=false
chk2_desc="Is package jq no longer held?"
chk2_det=""

chk3_pass=false
chk3_desc="Is lplab-tool installed via dpkg and does /usr/local/bin/lplab-tool run?"
chk3_det=""

chk4_pass=false
chk4_desc="Does /var/tmp/curl-owner.txt contain curl?"
chk4_det=""

# Check 1: apt-get check
if apt-get check >/dev/null 2>&1; then
    chk1_pass=true
    chk1_det="apt-get check passed cleanly."
else
    chk1_det="apt-get check failed (check /etc/apt/sources.list.d/broken-internal.list)."
fi

# Check 2: jq unheld
if ! apt-mark showhold 2>/dev/null | grep -qx 'jq'; then
    chk2_pass=true
    chk2_det="jq is not on hold."
else
    chk2_det="jq is still held by apt-mark."
fi

# Check 3: lplab-tool installed and runnable
pkg_status=$(dpkg-query -W -f='${Status}' lplab-tool 2>/dev/null || echo "")
tool_out=""
if [ -x /usr/local/bin/lplab-tool ]; then
    tool_out=$(/usr/local/bin/lplab-tool 2>/dev/null || echo "")
fi

if [ "$pkg_status" = "install ok installed" ] && [ "$tool_out" = "lplab-tool 1.0" ]; then
    chk3_pass=true
    chk3_det="lplab-tool installed and runs cleanly."
else
    chk3_det="status=${pkg_status}, output=${tool_out}"
fi

# Check 4: /var/tmp/curl-owner.txt
if [ -f /var/tmp/curl-owner.txt ]; then
    owner=$(tr -d ' \t\r\n' < /var/tmp/curl-owner.txt)
    if [ "$owner" = "curl" ]; then
        chk4_pass=true
        chk4_det="/var/tmp/curl-owner.txt contains curl."
    else
        chk4_det="Got '${owner}' instead of 'curl'."
    fi
else
    chk4_det="/var/tmp/curl-owner.txt is missing."
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
  "lab_id": "lab-19",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-apt-sources",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-apt-unhold",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-dpkg-install",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-dpkg-owner",
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
