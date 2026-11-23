# IT Support Work Order: TICKET-8921

**Assigned Host:** `rocky-core-01` (`rockylinux-9`)  
**Priority:** High  
**Classification:** Incident / Service Degradation  

---

### Incident Summary
Following scheduled maintenance and reboot, the primary data ingestion daemon `app-worker.service` failed to initialize. Downstream queue processors are backing up, and storage monitoring has fired alerts regarding unconstrained log growth.

### Reported Symptoms & Constraints
1. **Missing Storage Mount:** The application volume designated for runtime state at `/mnt/appdata` is absent. The system fstab configuration contains errors referencing the backing image at `/var/lib/lplab/appdata.img`.
2. **Service Startup Inability:** Attempts to manage or start `app-worker.service` are rejected by systemd. The unit file configuration appears corrupted or disabled.
3. **Log Runaway Risk:** Debug logging in `/var/log/app-worker/debug.log` has grown excessively and is consuming root partition capacity without an active rotation policy.

### Acceptance Criteria
- `/mnt/appdata` must be successfully mounted to the loopback filesystem `/var/lib/lplab/appdata.img` and configured in `/etc/fstab` to mount automatically on future boots.
- `app-worker.service` must be unmasked, enabled, and in a running (`active`) state under systemd.
- `/var/log/app-worker/debug.log` must be rotated or truncated to under 5MB in size, and a valid logrotate definition must be installed at `/etc/logrotate.d/app-worker`.
