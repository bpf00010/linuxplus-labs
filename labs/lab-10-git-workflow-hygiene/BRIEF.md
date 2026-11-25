# Work Order: Git Workflow Hygiene — Merge Conflicts, Secret Removal, and Pre-Commit Hooks

**Incident Ticket:** DEV-40210  
**Target Host:** `lplab-10` (Ubuntu 24.04)  
**Assigned Student:** `sysadmin` (password: `linuxplus`)  

---

## Scenario Description

The operations scripts repository at `/srv/ops-scripts` has accumulated several hygiene issues. A feature branch `feature/alert-fix` must be merged into `main`, but a merge conflict exists on `config.env`. The team lead has specified that the correct timeout value is `TIMEOUT=60` from the feature branch.

Additionally, a secrets file `.env.secrets` was accidentally committed and must be removed from Git tracking (but kept on disk). The repository's pre-commit hook is broken and non-executable, preventing automated syntax checking of shell scripts.

---

## Tasks & Acceptance Criteria

1. **Merge Feature Branch:**
   - Check out `main` and merge `feature/alert-fix` into `main`.
   - Resolve the merge conflict on `config.env` by keeping `TIMEOUT=60`.
   - Commit the merge cleanly with no conflict markers remaining.

2. **Remove Secrets from Git Tracking:**
   - Remove `.env.secrets` from Git tracking using `git rm --cached .env.secrets`.
   - Add `.env.secrets` to the repository's `.gitignore` file.
   - Commit this change cleanly.

3. **Fix Pre-Commit Hook:**
   - Inspect `.git/hooks/pre-commit` and fix any script errors.
   - Make the hook executable (`chmod +x`).
   - The hook must validate all staged `.sh` files using `bash -n`.

4. **Create Annotated Tag:**
   - Create an annotated Git tag `v1.0.0` on the final `main` commit.

---

## Verification

Run verification in the desktop dashboard or via terminal:
```bash
lplab verify lab-10
```
