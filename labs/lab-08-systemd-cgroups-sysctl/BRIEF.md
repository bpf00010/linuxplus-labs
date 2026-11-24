# Work Order: Diagnose Resource Constraints with Systemd Cgroups and Sysctl

**Incident Ticket:** PRF-90214  
**Target Host:** `lplab-08` (Ubuntu 24.04 LTS)  
**Assigned Student:** `sysadmin` (password: `linuxplus`)  

---

## Scenario Description

Application developers report that `batch-worker.service` crashes continuously with memory exhaustion and file descriptor limit errors. Simultaneously, a rogue logging process is polluting disk storage, and the host virtual memory swappiness and inotify watch quotas need urgent optimization.

You must inspect the systemd unit failure reasons, relax the restrictive cgroup resource limits, mask the runaway logger, and apply optimized kernel parameters.

---

## Tasks & Acceptance Criteria

1. **Systemd Cgroup Resource Allocation:**
   - Diagnose `batch-worker.service` failure using `journalctl -u batch-worker` and `systemctl cat batch-worker.service`.
   - Update the systemd drop-in override `/etc/systemd/system/batch-worker.service.d/override.conf`:
     - Set `MemoryMax` to at least `128M` (e.g. `256M`).
     - Set `LimitNOFILE` to at least `1024` (e.g. `4096`).
   - Reload systemd (`systemctl daemon-reload`) and ensure `batch-worker.service` is enabled and actively running.

2. **Rogue Service Deactivation & Masking:**
   - Stop, disable, and **mask** `rogue-logger.service` (`systemctl mask rogue-logger.service`) to prevent any accidental startup.

3. **Kernel Parameter Persistence:**
   - Modify `/etc/sysctl.d/99-lab-perf.conf` to set:
     ```ini
     vm.swappiness = 10
     fs.inotify.max_user_watches = 65536
     ```

4. **Live Sysctl Activation:**
   - Apply the sysctl configuration using `sysctl --system` (or `sysctl -p /etc/sysctl.d/99-lab-perf.conf`).
   - Ensure the live runtime parameters reflect `vm.swappiness = 10` and `fs.inotify.max_user_watches = 65536`.

---

## Verification

Run verification in the desktop dashboard or via terminal:
```bash
lplab verify lab-08
```
