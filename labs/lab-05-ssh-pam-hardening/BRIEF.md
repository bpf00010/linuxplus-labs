# Security Audit Remediation Ticket: SEC-AUDIT-518

**Assigned Host:** `rocky-core-ssh` (`rockylinux-9`)  
**Priority:** High  
**Classification:** Information Security / Access Control Hardening  

---

### Audit Finding Summary
An internal security baseline assessment identified high-risk vulnerabilities in the remote access configuration of production host `rocky-core-ssh`:
1. The OpenSSH daemon currently permits direct root login (`PermitRootLogin yes`) and password-based authentication (`PasswordAuthentication yes`), exposing the host to credential stuffing and brute-force attacks.
2. SSH daemon access is not constrained to authorized groups.
3. The operational administration account `opsadmin` has world-writable permissions on its `.ssh` directory and key files, and is not enrolled in the mandatory `sshusers` group.
4. Account password aging for `opsadmin` is disabled (`99999` days), in violation of company policy.

### Acceptance Criteria
- OpenSSH daemon configuration syntax check (`sshd -t`) must pass without errors, and the active configuration query (`sshd -T`) must report:
  - `permitrootlogin no`
  - `passwordauthentication no`
  - `allowgroups` containing `sshusers`
- User `opsadmin` must be added as a member of group `sshusers`.
- `/home/opsadmin/.ssh` directory must have permissions `0700` owned by `opsadmin`.
- `/home/opsadmin/.ssh/authorized_keys` file must have permissions `0600` owned by `opsadmin`.
- `chage -l opsadmin` must report a `Maximum number of days between password change` of `90` days (or less, greater than 0).
