# IT Operations Support Ticket: TICKET-4412

**Assigned Host:** `ubuntu-srv-04` (`ubuntu-24.04`)  
**Priority:** High  
**Classification:** Automation & Service Reliability  

---

### Incident Summary
The monitoring daemon `metrics-collector.service` periodically terminates unexpectedly, causing telemetric blackouts. An obsolete cron job in `/etc/cron.d/` was intended to monitor it, but the job is broken and unmanaged. Engineering policy mandates transitioning all recurring system maintenance to native `systemd` timers with central `journald` logging.

### Operational Requirements
1. **Watchdog Script Implementation:**
   - Create an executable Bash script at `/usr/local/bin/metrics-watchdog.sh` (permissions `0755`).
   - The script must inspect whether `metrics-collector.service` is active.
   - If `metrics-collector.service` is NOT active, the script must restart/start it (`systemctl restart metrics-collector.service` or `systemctl start metrics-collector.service`) AND log an alert entry to the system journal using `logger -t metrics-watchdog "metrics-collector restarted"`.
2. **Systemd Timer & Service Setup:**
   - Create a timer unit at `/etc/systemd/system/metrics-watchdog.timer` configured to run every 1 minute (`OnCalendar=*:*` or `OnUnitActiveSec=1m` / `OnBootSec=1m`).
   - Create its companion service unit at `/etc/systemd/system/metrics-watchdog.service` that triggers `/usr/local/bin/metrics-watchdog.sh`.
   - Enable and start `metrics-watchdog.timer` so it runs continuously in the background.
3. **Current Service State:**
   - Ensure `metrics-collector.service` is actively running.
