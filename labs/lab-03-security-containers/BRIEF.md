# Lab 03: Shared Directory ACLs and Sudoers

**Distro:** Rocky Linux 9 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Security, Users — group ownership, setgid, POSIX ACLs, visudo

## Goal
`/srv/shared-app` blocks group `webops` access, and user `deploy` has unrestricted `NOPASSWD: ALL` sudo rights in `/etc/sudoers.d/99-deploy`.

## Tasks
1. Set group owner of `/srv/shared-app` to `webops` and permissions to `2770` or `2775` (setgid).
2. Add a default POSIX ACL on `/srv/shared-app` so group `webops` inherits `rwx` permissions.
3. Ensure `/etc/sudoers.d/99-deploy` passes `visudo -cf /etc/sudoers.d/99-deploy`.
4. Restrict user `deploy` in `/etc/sudoers.d/99-deploy` to `NOPASSWD: /usr/bin/systemctl restart app-proxy` (or `systemctl restart app-proxy`) with no `ALL` rights.
