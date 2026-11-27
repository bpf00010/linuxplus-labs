# Lab 14: DNS, Socket Activation, and Logs

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Troubleshooting, Services, Scripting — dnsmasq, dig, systemd socket, awk

## Goal
`lab-dns.service` fails to start and points `db.lab.internal` to the wrong IP, `diag-echo.socket` listens on the wrong port, and `/var/log/lab-access.log` needs HTTP 500 analysis.

## Tasks
1. Fix `/etc/lab-dns/dnsmasq.conf` (remove invalid option, set `db.lab.internal` to `10.20.30.40`), then enable and start `lab-dns.service`.
2. Confirm `dig @127.0.0.1 -p 18053 status.lab.internal TXT +short` returns `"operational"`.
3. Update `/etc/systemd/system/diag-echo.socket` to listen on `127.0.0.1:18070`, reload systemd, and enable and start it so connecting returns `DIAG_OK`.
4. Parse `/var/log/lab-access.log` and write `/var/tmp/incident-summary.json` as `{"top_ip": "<IP>", "error_500_count": <N>}` for the IP with the most HTTP `500` responses.
