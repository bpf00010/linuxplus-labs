# Lab 19: APT Sources, Holds, and DPKG

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** System Management, Troubleshooting — apt, apt-mark, dpkg, dpkg -S

## Goal
APT is broken by an invalid source entry, `jq` is held, and a local `.deb` package needs installation and file-ownership inspection.

## Tasks
1. Fix or remove `/etc/apt/sources.list.d/broken-internal.list` so `apt-get check` passes cleanly.
2. Remove the package hold on `jq` (`apt-mark unhold jq`).
3. Install `/var/tmp/lplab-tool_1.0_all.deb` with `dpkg` so `/usr/local/bin/lplab-tool` runs.
4. Find which package owns `/usr/bin/curl` and write only that package name (`curl`) to `/var/tmp/curl-owner.txt`.
