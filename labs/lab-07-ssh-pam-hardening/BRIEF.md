# Work Order: Harden OpenSSH Daemon and User Password Aging Compliance

**Incident Ticket:** SEC-77104  
**Target Host:** `lplab-07` (Ubuntu 24.04 LTS)  
**Assigned Student:** `sysadmin` (password: `linuxplus`)  

---

## Scenario Description

A routine security compliance scan flagged multiple critical findings on `lplab-07`:
1. The OpenSSH daemon permits direct `root` logins and allows password authentication.
2. SSH access is unrestricted by group policy.
3. The operational admin account (`opsadmin`) has insecure file permissions on its `.ssh` directory and authorized keys.
4. User password expiration is set to `99999` days, violating the organization's 90-day password aging policy.

You must remediate the OpenSSH configuration, enforce group access controls, fix user SSH key permissions, and bring account aging into compliance.

---

## Tasks & Acceptance Criteria

1. **OpenSSH Daemon Hardening:**
   - Update `/etc/ssh/sshd_config.d/99-lab-audit.conf` (or main `/etc/ssh/sshd_config`):
     - `PermitRootLogin no`
     - `PasswordAuthentication no`
     - `AllowGroups sshusers`
   - Validate configuration with `sshd -t` (must pass without errors).
   - Ensure `sshd -T` reflects these directives.

2. **Systemd Service Reliability:**
   - Ensure the SSH service (`ssh.service` or `ssh.socket`) is enabled and active under systemd (`systemctl restart ssh || systemctl restart ssh.socket`).

3. **User Group & SSH Directory Permissions:**
   - Add user `opsadmin` to group `sshusers` (`usermod -aG sshusers opsadmin`).
   - Secure the user's SSH files:
     - `/home/opsadmin/.ssh` must be owned by `opsadmin:opsadmin` with permissions `0700` (`rwx------`).
     - `/home/opsadmin/.ssh/authorized_keys` must be owned by `opsadmin:opsadmin` with permissions `0600` (`rw-------`).

4. **Password Aging Policy:**
   - Use `chage` to configure the maximum password lifetime for `opsadmin` between `1` and `90` days (e.g. `chage -M 90 opsadmin`).

---

## Verification

Run verification in the desktop dashboard or via terminal:
```bash
lplab verify lab-07
```
