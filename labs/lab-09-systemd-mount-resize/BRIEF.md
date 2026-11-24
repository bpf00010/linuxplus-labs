# Work Order: Manage Systemd Mount Units and Online Filesystem Expansion

**Incident Ticket:** STR-66019  
**Target Host:** `lplab-09` (Rocky Linux 9)  
**Assigned Student:** `sysadmin` (password: `linuxplus`)  

---

## Scenario Description

The backup subsystem failed to mount storage for `/mnt/archive` on boot. An audit of `/etc/systemd/system/mnt-archive.mount` indicates that the unit references an invalid backing image file and omits required security flags (`nodev`, `nosuid`, `noexec`).

Furthermore, the downstream data service `archive-sync.service` is in a failed state due to unsatisfied unit dependencies, and the storage backing image must be enlarged to accommodate increased archive capacity.

---

## Tasks & Acceptance Criteria

1. **Storage Backing File Expansion:**
   - The backing loop image at `/var/lib/lplab/archive.img` was initialized at 32MB.
   - Enlarge the file to at least `96MB` (e.g. `128MB` using `truncate -s 128M /var/lib/lplab/archive.img` or `dd`).
   - Run `e2fsck -f /var/lib/lplab/archive.img` and `resize2fs /var/lib/lplab/archive.img` to expand the `ext4` filesystem cleanly.

2. **Systemd Mount Unit Configuration:**
   - Configure `/etc/systemd/system/mnt-archive.mount`:
     - `What=/var/lib/lplab/archive.img`
     - `Where=/mnt/archive`
     - `Type=ext4`
     - `Options=loop,nodev,nosuid,noexec`
     - `WantedBy=multi-user.target`
   - Reload systemd daemon (`systemctl daemon-reload`).
   - Enable and start `mnt-archive.mount` (`systemctl enable --now mnt-archive.mount`).

3. **Mount Verification:**
   - Confirm `/mnt/archive` is mounted and active with all three security options: `nodev`, `nosuid`, and `noexec`.
   - Verify that the mounted filesystem capacity reported by `df` is at least `85MB`.

4. **Service Synchronization:**
   - Ensure `archive-sync.service` is enabled and actively running without dependency failures.

---

## Verification

Run verification in the desktop dashboard or via terminal:
```bash
lplab verify lab-09
```
