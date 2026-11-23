# IT Support Work Order: TICKET-9044

**Assigned Host:** `ubuntu-gateway-01` (`ubuntu-24.04`)  
**Priority:** High  
**Classification:** Incident / Network & Service Connectivity  

---

### Incident Summary
Internal integration testing against the local microservice API gateway (`http://api.lab.internal:18080/health`) is failing. Automated health checkers report connection timeouts, and the reverse proxy service appears stopped or failing to reload.

### Reported Symptoms & Constraints
1. **Web Server Failure:** The Nginx reverse proxy service cannot be started or reloaded. Configuration syntax checks report an error within site definitions.
2. **Firewall Filter Block:** A scoped packet-filtering table (`table inet lplab02`) has a policy dropping traffic destined for the application port TCP 18080.
   > **Important Safety Notice:** WSL2 instances share a single kernel network namespace. Do NOT execute global firewall flushes (`nft flush ruleset` or `iptables -F`). Only manage the dedicated `inet lplab02` table.
3. **Local Resolution Mismatch:** The hostname `api.lab.internal` does not map to the primary loopback interface `127.0.0.1` in `/etc/hosts`.

### Acceptance Criteria
- `nginx -t` must pass without errors, and `nginx` service must be active and running under systemd.
- `/etc/hosts` must map `api.lab.internal` directly to `127.0.0.1`.
- The dedicated `table inet lplab02` firewall table must remain present and active, but must permit inbound traffic on TCP port 18080.
- Executing `curl -fsS http://api.lab.internal:18080/health` must succeed and return HTTP 200 with the payload `{"status":"healthy","service":"internal-api"}`.
