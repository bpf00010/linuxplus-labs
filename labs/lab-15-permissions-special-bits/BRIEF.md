# Lab 15: File Permissions, Special Bits, and Links

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Security, System Management — chmod, SUID, SGID, sticky bit, links, umask

## Goal
Fix insecure special permissions on a binary and shared dropbox directory, repair a broken symlink, create a hard link, and set `dev1`'s default `umask`.

## Tasks
1. Remove the SUID bit from `/usr/local/bin/legacy-helper` so its mode is `0755`.
2. Set `/srv/dropbox` group owner to `devteam` with SGID and Sticky Bit enabled (`3770` or `3775`).
3. Point symlink `/srv/app/current.conf` to `/srv/app/config.v2`, and create a hard link `/srv/app/readme.hard` pointing to `/srv/app/readme.txt`.
4. Set `umask 0027` in `/home/dev1/.bashrc` and remove `umask 0000`.
