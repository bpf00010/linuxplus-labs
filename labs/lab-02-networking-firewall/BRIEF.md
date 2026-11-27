# Lab 02: Fix Nginx, Hosts, and Firewall

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Services, Security, Troubleshooting — nginx, /etc/hosts, nftables, curl

## Goal
`http://api.lab.internal:18080/health` is unreachable due to an Nginx config syntax error, a wrong `/etc/hosts` IP, and a firewall drop rule in `table inet lplab02`.

## Tasks
1. Fix the syntax error in `/etc/nginx/sites-available/internal-api`, confirm `nginx -t` passes, and start `nginx`.
2. Update `/etc/hosts` so `api.lab.internal` maps to `127.0.0.1`.
3. Remove the TCP port `18080` drop rule from nftables `table inet lplab02`.
4. Confirm `curl -fsS http://api.lab.internal:18080/health` returns HTTP 200 with `"status":"healthy"`.

## Rules
- Do not delete `table inet lplab02` or run `nft flush ruleset` or `iptables -F`.
