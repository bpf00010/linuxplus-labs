# Work Order: PKI Certificate Authority Trust Chain and Nginx TLS Repair

**Incident Ticket:** SEC-71803  
**Target Host:** `lplab-11` (Ubuntu 24.04)  
**Assigned Student:** `sysadmin` (password: `linuxplus`)  

---

## Scenario Description

The internal web portal `portal.lab.internal` is served by Nginx on `127.0.0.1:18450` over TLS. Currently the portal uses a broken self-signed certificate with the wrong Common Name (`wrong.local`) and no Subject Alternative Name for `portal.lab.internal`. The certificate is also not signed by the internal Root CA located at `/etc/lab-ca/ca.crt`.

The internal Root CA is not yet installed in the Ubuntu system trust store, so even a correctly-signed certificate will fail standard `curl` verification.

---

## Tasks & Acceptance Criteria

1. **Generate and Sign a New Certificate:**
   - Generate a new private key at `/etc/ssl/lab-portal/portal.key` with mode `0600`.
   - Create a CSR for `portal.lab.internal` with `subjectAltName = DNS:portal.lab.internal`.
   - Sign the CSR using `/etc/lab-ca/ca.crt` and `/etc/lab-ca/ca.key` to produce `/etc/ssl/lab-portal/portal.crt`.

2. **Install Internal CA into System Trust Store:**
   - Copy `/etc/lab-ca/ca.crt` to `/usr/local/share/ca-certificates/lab-ca.crt`.
   - Run `update-ca-certificates` to install it into the system trust store.

3. **Reload Nginx and Verify:**
   - Reload `nginx.service` so it picks up the new certificate.
   - Verify that `curl -fsS https://portal.lab.internal:18450/` succeeds WITHOUT the `-k` or `--insecure` flag and returns HTTP 200 containing `"trusted"`.

---

## Verification

Run verification in the desktop dashboard or via terminal:
```bash
lplab verify lab-11
```
