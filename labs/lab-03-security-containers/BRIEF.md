# Security Audit Remediation Ticket: SEC-AUDIT-402

**Assigned Host:** `rocky-app-02` (`rockylinux-9`)  
**Priority:** Urgent  
**Classification:** Security Non-Conformance / Access Control  

---

### Audit Finding Summary
An internal security compliance audit discovered significant security violations on production host `rocky-app-02`. Access permissions violate multi-user collaboration standards, and privilege delegation for deployment service accounts breaches the principle of least privilege.

### Reported Non-Conformances
1. **Shared Workspace Isolation:** The application deployment root `/srv/shared-app` is locked down to `root:root` with mode `0700`. The development/operations group `webops` has no access, and newly created files do not inherit group ownership or appropriate collaboration permissions.
2. **Excessive Sudo Privileges:** The service account `deploy` has been granted blanket root access (`NOPASSWD: ALL`) via `/etc/sudoers.d/99-deploy`. Policy mandates that service accounts only possess exact command privileges required for continuous deployment.

### Acceptance Criteria
- Group ownership of `/srv/shared-app` must be set to `webops`.
- Directory permissions on `/srv/shared-app` must enforce the setgid bit (`2770` or `2775`) to preserve group ownership on newly created items.
- POSIX Default Access Control Lists (ACLs) must be configured on `/srv/shared-app` so that group `webops` automatically receives `rwx` permissions on newly created files and subdirectories.
- `/etc/sudoers.d/99-deploy` must pass syntax validation (`visudo -cf /etc/sudoers.d/99-deploy`).
- The `deploy` user must be permitted to execute `systemctl restart app-proxy` (or `/usr/bin/systemctl restart app-proxy`) with `NOPASSWD`, and must NOT possess any generic `ALL` administrative execution rights.
