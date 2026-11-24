# Work Order: Automate Service Watchdog with Systemd Timers and Logging

**Incident Ticket:** INC-84021  
**Target Host:** `lplab-04` (Ubuntu 24.04 LTS)  
**Assigned Student:** `sysadmin` (password: `linuxplus`)  

---

## Scenario Description

The infrastructure team reported that `metrics-collector.service` periodically terminates during burst traffic. A legacy cron job was previously placed at `/etc/cron.d/metrics-watchdog` to monitor and restart it, but the job is failing silently and lacks auditing integration.

The department standard requires all periodic monitoring and recovery automation to use native **systemd timer** and **service** units with direct output streaming to `journald`.

---

## Tasks & Acceptance Criteria

1. **Watchdog Recovery Script:**
   - Create an executable Bash script at `/usr/local/bin/metrics-watchdog.sh` (mode `0755`, owned by `root:root`).
   - The script must check whether `metrics-collector.service` is actively running.
   - If the service is NOT active, the script must:
     - Restart or start `metrics-collector.service`.
     - Log an audit message containing `"metrics-collector restarted"` to journald via `logger -t metrics-watchdog`.
   - The script must pass `bash -n` validation.

2. **Systemd Service & Timer Units:**
   - Create `/etc/systemd/system/metrics-watchdog.service`:
     - Type: `oneshot`
     - ExecStart: `/usr/local/bin/metrics-watchdog.sh`
   - Create `/etc/systemd/system/metrics-watchdog.timer`:
     - Configured to trigger every 1 minute (`OnUnitActiveSec=1min` or `OnCalendar=minutely` or `OnCalendar=*:0/1`).
     - Installed into `timers.target`.
   - Reload systemd and enable and start `metrics-watchdog.timer` (`systemctl enable --now metrics-watchdog.timer`).

3. **Legacy Decommission:**
   - Remove the unmanaged legacy cron job `/etc/cron.d/metrics-watchdog`.

4. **Collector Service Health:**
   - Ensure `metrics-collector.service` is enabled and actively running.

---

## Verification

Run verification in the desktop dashboard or via terminal:
```bash
lplab verify lab-04
```
