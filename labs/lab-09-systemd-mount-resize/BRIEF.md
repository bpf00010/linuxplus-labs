# Lab 09: Systemd Mount and Filesystem Resize

**Distro:** Rocky Linux 9 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** System Management, Troubleshooting — systemd .mount units, mount options, resize2fs

## Goal
`/etc/systemd/system/mnt-archive.mount` points to a missing image and lacks security options, `/var/lib/lplab/archive.img` is only 32MB, and `archive-sync.service` is stopped.

## Tasks
1. Fix `/etc/systemd/system/mnt-archive.mount` (`What=/var/lib/lplab/archive.img`, `Where=/mnt/archive`, `Type=ext4`, `Options=loop,nodev,nosuid,noexec`).
2. Expand `/var/lib/lplab/archive.img` (e.g., to `128M`) and run `e2fsck -f` and `resize2fs` so `/mnt/archive` is at least `85MB`.
3. Reload systemd, then enable and start `mnt-archive.mount`.
4. Enable and start `archive-sync.service`.
