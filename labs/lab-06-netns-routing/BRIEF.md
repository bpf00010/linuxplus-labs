# Network Operations Ticket: NET-OPS-604

**Assigned Host:** `ubuntu-netns-06` (`ubuntu-24.04`)  
**Priority:** High  
**Classification:** Container Networking / Inter-Namespace Routing  

---

### Incident Summary
An isolated internal microservice running inside dedicated network namespace `app-ns` is unreachable from the host namespace. Automated health probes to `http://10.250.10.2:18090/health` report connection failure or destination host unreachable.

### Architecture Overview
- Host root namespace interface: `veth-host` configured with `10.250.10.1/24`.
- Isolated container namespace: `app-ns` containing interface `veth-app` configured with `10.250.10.2/24`.
- Service endpoint inside `app-ns`: HTTP health server listening on `10.250.10.2:18090`.

### Acceptance Criteria
1. Interface `veth-host` in the root namespace and `veth-app` inside `app-ns` must both be in the `UP` state with IP addresses `10.250.10.1/24` and `10.250.10.2/24` respectively.
2. The network namespace `app-ns` must have a valid default gateway route configured via `10.250.10.1`.
3. Inbound traffic on TCP port `18090` must be accepted by packet filtering rules inside `app-ns` (remove or update the drop rule in table `inet ns_filter` inside `app-ns`).
4. Executing `curl -fsS --max-time 3 http://10.250.10.2:18090/health` from the root namespace must succeed and return HTTP 200 with JSON payload `{"status":"ok","service":"isolated-microservice"}`.
