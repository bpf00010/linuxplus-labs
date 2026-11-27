# Lab 01: Fix Broken Mount and Service

**Distro:** Rocky Linux 9 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** System Management, Troubleshooting — fstab, mounts, systemd units, logrotate

## Goal
The `/mnt/appdata` mount is missing, `app-worker.service` is masked with a bad `ExecStart` path, and `/var/log/app-worker/debug.log` is over 5MB with no logrotate rule.

## Tasks
1. Fix `/etc/fstab` to mount `/var/lib/lplab/appdata.img` on `/mnt/appdata` (`ext4`, `loop,defaults`) and mount it.
2. Fix `ExecStart` in `/etc/systemd/system/app-worker.service` to `/usr/local/bin/app-worker`, then unmask, enable, and start it.
3. Reduce `/var/log/app-worker/debug.log` to 5MB or less and create `/etc/logrotate.d/app-worker`.
