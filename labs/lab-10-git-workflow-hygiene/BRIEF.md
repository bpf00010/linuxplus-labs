# Lab 10: Git Merge, Secrets, and Hooks

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Automation & Scripting, Security — git merge, .gitignore, hooks, tags

## Goal
The repository at `/srv/ops-scripts` has an unmerged branch `feature/alert-fix`, a tracked `.env.secrets` file, and a broken `.git/hooks/pre-commit` hook.

## Tasks
1. On branch `main` in `/srv/ops-scripts`, merge `feature/alert-fix`, resolve `config.env` keeping `TIMEOUT=60` with no conflict markers, and commit cleanly.
2. Remove `.env.secrets` from Git tracking (`git rm --cached .env.secrets`), add `.env.secrets` to `.gitignore`, and commit.
3. Fix the syntax error in `.git/hooks/pre-commit`, make it executable (`chmod +x`), and ensure it validates staged `.sh` files using `bash -n`.
4. Create an annotated tag `v1.0.0` on `main` HEAD.
