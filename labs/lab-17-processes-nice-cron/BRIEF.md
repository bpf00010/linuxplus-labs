# Lab 17: Processes, Nice Priority, and Cron

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** System Management, Troubleshooting — ps/pgrep, nice, systemd, cron.allow, crontab

## Goal
`cpu-hog.service` is consuming CPU, `batch-job.service` runs at default niceness (`0`), cron access is unrestricted, and `sysadmin` has no heartbeat cron job.

## Tasks
1. Stop and disable `cpu-hog.service` so no `cpu-hog.sh` process is running.
2. Configure `batch-job.service` with `Nice=15`, reload systemd, and restart it so its running process has niceness `15`.
3. Create `/etc/cron.allow` listing only `root` and `sysadmin` (not `cronuser`).
4. Add a `sysadmin` crontab entry running `/usr/local/bin/heartbeat.sh` every 5 minutes (`*/5 * * * *`) and ensure `cron.service` is active.
