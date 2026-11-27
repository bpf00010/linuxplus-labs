# Lab 11: Local CA Trust and Nginx TLS

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Security, Services, Troubleshooting — openssl CSR/SAN, CA signing, trust store, nginx

## Goal
Nginx serves `portal.lab.internal` on `127.0.0.1:18450` using an untrusted self-signed cert for `wrong.local`, and `/etc/lab-ca/ca.crt` is not in the system trust store.

## Tasks
1. Set `/etc/ssl/lab-portal/portal.key` mode to `0600` and sign `/etc/ssl/lab-portal/portal.crt` using `/etc/lab-ca/ca.crt` and `/etc/lab-ca/ca.key`.
2. Ensure `/etc/ssl/lab-portal/portal.crt` includes SAN `DNS:portal.lab.internal`.
3. Copy `/etc/lab-ca/ca.crt` to `/usr/local/share/ca-certificates/lab-ca.crt`, run `update-ca-certificates`, and reload `nginx.service`.
4. Confirm `curl -fsS https://portal.lab.internal:18450/` succeeds without `-k` and returns `"trusted"`.
