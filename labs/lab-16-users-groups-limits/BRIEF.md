# Lab 16: Users, Groups, Skel, and Limits

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Services & Users, Security — /etc/skel, useradd, usermod, chage, limits.d

## Goal
Configure default home templates in `/etc/skel`, provision `appuser` in group `ops` with open-file limits, and disable the `formeremp` account.

## Tasks
1. Create `/etc/skel/WELCOME.txt` and directory `/etc/skel/bin`.
2. Create group `ops` and user `appuser` with home directory from `/etc/skel`, shell `/bin/bash`, and secondary group `ops`.
3. Lock account `formeremp`, set its shell to `/usr/sbin/nologin`, and expire the account (`chage -E 0` or past date).
4. Create `/etc/security/limits.d/99-appuser.conf` setting `appuser` soft `nofile` to `4096` and hard `nofile` to `8192`.
