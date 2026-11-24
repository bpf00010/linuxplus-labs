# Work Order: Resolve Reverse Proxy Port Conflicts and Harden TLS Configuration

**Incident Ticket:** SEC-59021  
**Target Host:** `lplab-06` (Ubuntu 24.04 LTS)  
**Assigned Student:** `sysadmin` (password: `linuxplus`)  

---

## Scenario Description

The internal portal reverse proxy failed to start following maintenance. Operations reports that `nginx.service` fails during startup with socket binding errors, security audits flagged improper permissions on private TLS certificates, and upstream proxy traffic is returning connection refused errors.

You must identify and eliminate the port conflict, fix TLS certificate permissions, correct Nginx configuration directives, and restore HTTPS access to the portal backend.

---

## Tasks & Acceptance Criteria

1. **Port Conflict Resolution:**
   - A rogue or legacy service is squatting on TCP port `127.0.0.1:18443`.
   - Identify the service (`legacy-stub.service`). Stop and disable it so it no longer runs or binds port `18443`.

2. **TLS Key Security Hardening:**
   - Security policy requires private keys to be accessible strictly by `root`.
   - Ensure `/etc/ssl/portal/portal.key` is owned by `root:root` with permissions mode `0600` (or `-rw-------`).

3. **Nginx Site Configuration:**
   - Fix `/etc/nginx/sites-available/portal-tls`:
     - Correct `ssl_certificate_key` to point to `/etc/ssl/portal/portal.key` (fixing the missing key path typo).
     - Correct the upstream `proxy_pass` to target the active backend service on `http://127.0.0.1:18445` (instead of port 18444).
   - Ensure the site is enabled in `/etc/nginx/sites-enabled/`.
   - Verify that `nginx -t` passes with zero errors.

4. **Service Health & Ingress Test:**
   - Enable and start `nginx.service`.
   - Verify that `curl -kfsS --max-time 3 https://127.0.0.1:18443/` returns HTTP `200` containing `"healthy"`.

---

## Verification

Run verification in the desktop dashboard or via terminal:
```bash
lplab verify lab-06
```
