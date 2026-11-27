# Lab 18: Text Processing, Find, and Scripting

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Automation & Scripting, System Management — grep, awk, sed, sort/uniq, find, bash

## Goal
Filter a CSV user list, update a config hostname, clean oversized `.tmp` files, and write a file-check Bash script.

## Tasks
1. Extract all unique, alphabetically sorted usernames with status `active` from `/srv/data/users.csv` (one per line, no header) into `/srv/data/active_users.txt`.
2. Replace every occurrence of `old-db.internal` with `prod-db.internal` in `/srv/data/app.conf`.
3. Find and delete all `*.tmp` files larger than 1MB inside `/srv/data/files/` while keeping `.log` files and smaller `.tmp` files.
4. Write an executable Bash script `/usr/local/bin/check-file.sh` that checks `$1`: prints `EXISTS` and exits `0` if the file exists, or prints `MISSING` and exits `1` if it does not.
