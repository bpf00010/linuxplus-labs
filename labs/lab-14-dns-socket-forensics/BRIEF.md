# Work Order: DNS Service Repair, Socket Activation, and Log Forensics

**Incident Ticket:** NET-91674  
**Target Host:** `lplab-14` (Ubuntu 24.04)  
**Assigned Student:** `sysadmin` (password: `linuxplus`)  

---

## Scenario Description

Three independent subsystems are broken on this host:

1. **DNS Service:** A scoped DNS service (`lab-dns.service`) running `dnsmasq` on `127.0.0.1:18053` has a typo in its configuration file and an invalid option causing it to fail on startup. It should resolve `db.lab.internal` to `10.20.30.40` and serve a TXT record for `status.lab.internal` with value `"operational"`.

2. **Socket-Activated Echo Service:** A `systemd` socket-activation pair (`diag-echo.socket` + `diag-echo@.service`) is configured to listen on `127.0.0.1:18070` and echo `DIAG_OK` to any connecting client. The socket unit has the wrong port (`18071`), and both units are stopped/disabled.

3. **Log Forensics:** The file `/var/log/lab-access.log` contains 200 synthetic HTTP access log entries. Some client IPs are generating HTTP `500` errors. You must identify the top offending IP and its exact `500` error count.

---

## Tasks & Acceptance Criteria

1. **Repair DNS Service:**
   - Fix `/etc/lab-dns/dnsmasq.conf` so that `lab-dns.service` starts cleanly.
   - Ensure `dig @127.0.0.1 -p 18053 db.lab.internal +short` returns `10.20.30.40`.
   - Ensure `dig @127.0.0.1 -p 18053 status.lab.internal TXT +short` returns `"operational"`.

2. **Fix Socket Activation:**
   - Fix `/etc/systemd/system/diag-echo.socket` to listen on `127.0.0.1:18070`.
   - Enable and start `diag-echo.socket`.
   - Verify that connecting to `127.0.0.1:18070` returns `DIAG_OK`.

3. **Log Forensics:**
   - Analyze `/var/log/lab-access.log` and identify the client IP with the most HTTP `500` responses.
   - Write `/var/tmp/incident-summary.json` with format: `{"top_ip": "<IP>", "error_500_count": <N>}`.

---

## Verification

Run verification in the desktop dashboard or via terminal:
```bash
lplab verify lab-14
```
