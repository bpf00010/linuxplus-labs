# Lab 08: Systemd Cgroups and Sysctl Tuning

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Troubleshooting, System Management — systemd drop-ins, cgroups, mask, sysctl

## Goal
`batch-worker.service` crashes due to tight `MemoryMax` and `LimitNOFILE` limits, `rogue-logger.service` is spamming `/var/log/rogue.log`, and kernel sysctl values need tuning.

## Tasks
1. Edit `/etc/systemd/system/batch-worker.service.d/override.conf` to set `MemoryMax` >= `128M` and `LimitNOFILE` >= `1024`, reload systemd, and enable and start `batch-worker.service`.
2. Stop, disable, and mask `rogue-logger.service`.
3. Set `vm.swappiness = 10` and `fs.inotify.max_user_watches = 65536` in `/etc/sysctl.d/99-lab-perf.conf`.
4. Apply the sysctl settings (`sysctl --system`) so live kernel parameters match.
