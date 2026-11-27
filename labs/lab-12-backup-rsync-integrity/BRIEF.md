# Lab 12: Tar Restore, Rsync, and Checksums

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** System Management, Troubleshooting, Security — tar, rsync, symlinks, sha256sum

## Goal
`/srv/app-prod/` is corrupted and missing files. Restore it from `/var/backups/app-release.tar.gz`, mirror it cleanly, and create a verified `.tar.xz` backup.

## Tasks
1. Extract `/var/backups/app-release.tar.gz` into `/srv/app-prod/` so `bin/run.sh` is executable, `current.conf -> app.conf` is a symlink, and `sha256sum -c SHA256SUMS` passes.
2. Sync `/srv/app-prod/` to `/srv/backup-mirror/` using `rsync` while excluding `*.tmp` files and `cache/`.
3. Create `/var/backups/verified-mirror.tar.xz` containing `/srv/backup-mirror/` (including `app.conf`).
4. Create `/var/backups/verified-mirror.tar.xz.sha256` inside `/var/backups` so `sha256sum -c verified-mirror.tar.xz.sha256` passes.
