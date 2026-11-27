# Lab 06: Nginx TLS and Port Conflict

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Services, Security, Troubleshooting — socket ports, TLS key permissions, nginx

## Goal
Nginx cannot start on `127.0.0.1:18443` because `legacy-stub.service` holds the port, `/etc/ssl/portal/portal.key` has open permissions, and `/etc/nginx/sites-available/portal-tls` has wrong key and upstream settings.

## Tasks
1. Stop and disable `legacy-stub.service` to free TCP port `18443`.
2. Set `/etc/ssl/portal/portal.key` owner to `root:root` and mode to `0600`.
3. Fix `/etc/nginx/sites-available/portal-tls` (`ssl_certificate_key /etc/ssl/portal/portal.key;` and `proxy_pass http://127.0.0.1:18445;`), pass `nginx -t`, and enable and start `nginx`.
4. Confirm `curl -kfsS https://127.0.0.1:18443/` returns HTTP 200 containing `"healthy"`.
