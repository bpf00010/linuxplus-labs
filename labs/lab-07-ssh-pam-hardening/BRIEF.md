# Lab 07: SSH and Password Hardening

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Security, Services & Users — sshd_config, AllowGroups, .ssh permissions, chage

## Goal
OpenSSH allows root and password logins without group restrictions, `opsadmin` has open `.ssh` permissions, and `opsadmin` password max age is `99999` days.

## Tasks
1. Update `/etc/ssh/sshd_config.d/99-lab-audit.conf` to set `PermitRootLogin no`, `PasswordAuthentication no`, and `AllowGroups sshusers`, and verify with `sshd -t`.
2. Ensure `ssh.service` or `ssh.socket` is active under systemd.
3. Add `opsadmin` to group `sshusers` and set `opsadmin:opsadmin` ownership with mode `0700` on `/home/opsadmin/.ssh` and `0600` on `/home/opsadmin/.ssh/authorized_keys`.
4. Set `opsadmin` maximum password age between `1` and `90` days with `chage`.
