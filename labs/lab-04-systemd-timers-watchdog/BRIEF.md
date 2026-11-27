# Lab 04: Systemd Timer Watchdog Migration

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Automation, System Management — bash scripts, systemd timers, logger, cron

## Goal
A broken legacy cron job at `/etc/cron.d/metrics-watchdog` fails to monitor `metrics-collector.service`. Replace it with a Bash watchdog script and a systemd timer.

## Tasks
1. Create executable `/usr/local/bin/metrics-watchdog.sh` (`0755`, passes `bash -n`) that checks `metrics-collector.service` and starts it (and logs via `logger -t metrics-watchdog`) if inactive.
2. Create `/etc/systemd/system/metrics-watchdog.service` (`Type=oneshot`) and `/etc/systemd/system/metrics-watchdog.timer` (runs every minute), then enable and start `metrics-watchdog.timer`.
3. Remove `/etc/cron.d/metrics-watchdog`.
4. Enable `metrics-collector.service` and confirm `/usr/local/bin/metrics-watchdog.sh` restores it to `active` when stopped.
