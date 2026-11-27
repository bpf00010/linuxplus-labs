#!/usr/bin/env bash
# Non-destructive, idempotent verification script emitting strict JSON to stdout

chk1_pass=false
chk1_desc="Is main checked out, clean, merged with feature/alert-fix, and does config.env have TIMEOUT=60?"
chk1_det=""

chk2_pass=false
chk2_desc="Is .env.secrets listed in .gitignore and untracked by Git?"
chk2_det=""

chk3_pass=false
chk3_desc="Is .git/hooks/pre-commit executable, valid under bash -n, and checking staged scripts with bash -n?"
chk3_det=""

chk4_pass=false
chk4_desc="Does annotated tag v1.0.0 exist and point to main HEAD?"
chk4_det=""

cd /srv/ops-scripts 2>/dev/null || { echo '{"lab_id":"lab-10","passed":false,"score_passed":0,"score_total":4,"checks":[]}'; exit 1; }

GIT="git -c safe.directory=/srv/ops-scripts"

# Check 1: main checked out, clean tree, merged, TIMEOUT=60, no conflict markers
current_branch=$($GIT rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
tree_clean=false
$GIT diff --quiet 2>/dev/null && $GIT diff --cached --quiet 2>/dev/null && tree_clean=true
merged=false
$GIT merge-base --is-ancestor feature/alert-fix main 2>/dev/null && merged=true
has_timeout60=false
grep -qE '^TIMEOUT=60[[:space:]]*$' config.env 2>/dev/null && has_timeout60=true
no_markers=true
grep -qE '^(<<<<<<<|=======|>>>>>>>)' config.env 2>/dev/null && no_markers=false

if [ "$current_branch" = "main" ] && [ "$tree_clean" = true ] && [ "$merged" = true ] && [ "$has_timeout60" = true ] && [ "$no_markers" = true ]; then
    chk1_pass=true
    chk1_det="main clean, feature/alert-fix merged, TIMEOUT=60."
else
    chk1_det="branch=${current_branch}, clean=${tree_clean}, merged=${merged}, timeout60=${has_timeout60}, no_markers=${no_markers}"
fi

# Check 2: .env.secrets in .gitignore and not tracked
in_gitignore=false
grep -q '\.env\.secrets' .gitignore 2>/dev/null && in_gitignore=true
tracked_count=$($GIT ls-files -- .env.secrets 2>/dev/null | wc -l)
not_tracked=false
[ "$tracked_count" -eq 0 ] && not_tracked=true

if [ "$in_gitignore" = true ] && [ "$not_tracked" = true ]; then
    chk2_pass=true
    chk2_det=".env.secrets ignored and untracked."
else
    chk2_det="in_gitignore=${in_gitignore}, not_tracked=${not_tracked}"
fi

# Check 3: pre-commit hook exists, executable, passes bash -n, references bash -n
hook=".git/hooks/pre-commit"
hook_exists=false
hook_exec=false
hook_syntax=false
hook_refs_bashn=false

if [ -f "$hook" ]; then
    hook_exists=true
    [ -x "$hook" ] && hook_exec=true
    bash -n "$hook" 2>/dev/null && hook_syntax=true
    grep -q 'bash -n' "$hook" 2>/dev/null && hook_refs_bashn=true
fi

if [ "$hook_exists" = true ] && [ "$hook_exec" = true ] && [ "$hook_syntax" = true ] && [ "$hook_refs_bashn" = true ]; then
    chk3_pass=true
    chk3_det="pre-commit hook valid and executable."
else
    chk3_det="exists=${hook_exists}, exec=${hook_exec}, syntax=${hook_syntax}, bash_n=${hook_refs_bashn}"
fi

# Check 4: annotated tag v1.0.0 exists and points at main
tag_type=$($GIT cat-file -t v1.0.0 2>/dev/null || echo "")
tag_points_main=false
if [ "$tag_type" = "tag" ]; then
    tag_commit=$($GIT rev-list -n1 v1.0.0 2>/dev/null || echo "")
    main_commit=$($GIT rev-parse main 2>/dev/null || echo "")
    [ "$tag_commit" = "$main_commit" ] && [ -n "$tag_commit" ] && tag_points_main=true
fi

if [ "$tag_type" = "tag" ] && [ "$tag_points_main" = true ]; then
    chk4_pass=true
    chk4_det="Annotated tag v1.0.0 points to main HEAD."
else
    chk4_det="tag_type=${tag_type}, points_at_main=${tag_points_main}"
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
  "lab_id": "lab-10",
  "passed": ${overall_passed},
  "score_passed": ${score_passed},
  "score_total": 4,
  "checks": [
    {
      "id": "chk-merge-conflict",
      "description": "${chk1_desc}",
      "passed": ${chk1_pass},
      "details": "${chk1_det}"
    },
    {
      "id": "chk-secrets-removed",
      "description": "${chk2_desc}",
      "passed": ${chk2_pass},
      "details": "${chk2_det}"
    },
    {
      "id": "chk-precommit-hook",
      "description": "${chk3_desc}",
      "passed": ${chk3_pass},
      "details": "${chk3_det}"
    },
    {
      "id": "chk-annotated-tag",
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
