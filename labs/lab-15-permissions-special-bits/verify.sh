#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="Does /usr/local/bin/legacy-helper have mode 0755 with SUID removed?"
chk1_det=""

chk2_pass=false
chk2_desc="Does /srv/dropbox have group devteam and mode 3770 or 3775?"
chk2_det=""

chk3_pass=false
chk3_desc="Does current.conf point to /srv/app/config.v2 and is readme.hard hard-linked to readme.txt?"
chk3_det=""

chk4_pass=false
chk4_desc="Does /home/dev1/.bashrc set umask 0027 without umask 0000?"
chk4_det=""

# Check 1: SUID removed
helper_mode=$(stat -c '%a' /usr/local/bin/legacy-helper 2>/dev/null || echo "")
if [ "$helper_mode" = "755" ]; then
    chk1_pass=true
    chk1_det="legacy-helper mode is 0755."
else
    chk1_det="mode=${helper_mode} (expected 755)"
fi

# Check 2: /srv/dropbox group and special bits
db_grp=$(stat -c '%G' /srv/dropbox 2>/dev/null || echo "")
db_mode=$(stat -c '%a' /srv/dropbox 2>/dev/null || echo "")
if [ "$db_grp" = "devteam" ] && { [ "$db_mode" = "3770" ] || [ "$db_mode" = "3775" ]; }; then
    chk2_pass=true
    chk2_det="/srv/dropbox group is devteam with mode ${db_mode}."
else
    chk2_det="group=${db_grp}, mode=${db_mode} (expected devteam, 3770 or 3775)"
fi

# Check 3: Symlink and hard link
sym_ok=false
hard_ok=false

if [ -L /srv/app/current.conf ]; then
    resolved=$(readlink -f /srv/app/current.conf 2>/dev/null || echo "")
    [ "$resolved" = "/srv/app/config.v2" ] && sym_ok=true
fi

if [ -f /srv/app/readme.hard ] && [ ! -L /srv/app/readme.hard ] && [ -f /srv/app/readme.txt ]; then
    inode_txt=$(stat -c '%i' /srv/app/readme.txt 2>/dev/null || echo "a")
    inode_hard=$(stat -c '%i' /srv/app/readme.hard 2>/dev/null || echo "b")
    [ "$inode_txt" = "$inode_hard" ] && hard_ok=true
fi

if [ "$sym_ok" = true ] && [ "$hard_ok" = true ]; then
    chk3_pass=true
    chk3_det="Symlink and hard link verified."
else
    chk3_det="symlink_ok=${sym_ok}, hardlink_ok=${hard_ok}"
fi

# Check 4: umask 0027 in /home/dev1/.bashrc
has_0027=false
has_0000=false
if [ -f /home/dev1/.bashrc ]; then
    grep -qE '^[[:space:]]*umask[[:space:]]+0?027([[:space:]]|$)' /home/dev1/.bashrc && has_0027=true
    grep -qE '^[[:space:]]*umask[[:space:]]+0+([[:space:]]|$)' /home/dev1/.bashrc && has_0000=true
fi

if [ "$has_0027" = true ] && [ "$has_0000" = false ]; then
    chk4_pass=true
    chk4_det="/home/dev1/.bashrc sets umask 0027."
else
    chk4_det="has_0027=${has_0027}, has_0000=${has_0000}"
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
  "lab_id": "lab-15",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-suid-removed",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-dropbox-perms",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-links",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-umask",
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
