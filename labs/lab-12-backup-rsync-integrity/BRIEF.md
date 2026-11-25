# Work Order: Backup Restoration, Rsync Synchronization, and Integrity Verification

**Incident Ticket:** OPS-55270  
**Target Host:** `lplab-12` (Ubuntu 24.04)  
**Assigned Student:** `sysadmin` (password: `linuxplus`)  

---

## Scenario Description

The production deployment at `/srv/app-prod/` has been corrupted: critical files are missing or overwritten with garbage data, and junk files have accumulated. A clean golden backup tarball exists at `/var/backups/app-release.tar.gz` containing the original files with correct permissions and checksums.

Your task is to restore the production directory, synchronize it to a backup mirror, and create a verified compressed archive.

---

## Tasks & Acceptance Criteria

1. **Restore from Backup:**
   - Extract `/var/backups/app-release.tar.gz` into `/srv/app-prod/`, restoring all original files with correct permissions.
   - Ensure `bin/run.sh` is executable, the `current.conf -> app.conf` symlink is intact, and `SHA256SUMS` integrity check passes.
   - Remove any junk files (`debug.tmp`, `cache/stale.bin`, etc.) that are not part of the golden backup.

2. **Rsync to Backup Mirror:**
   - Synchronize `/srv/app-prod/` into `/srv/backup-mirror/` using `rsync`.
   - Exclude `*.tmp` files and `cache/` directories during synchronization.

3. **Create Verified Archive:**
   - Create a compressed archive `/var/backups/verified-mirror.tar.xz` of the contents of `/srv/backup-mirror/`.
   - Generate a SHA-256 checksum file at `/var/backups/verified-mirror.tar.xz.sha256`.

---

## Verification

Run verification in the desktop dashboard or via terminal:
```bash
lplab verify lab-12
```
