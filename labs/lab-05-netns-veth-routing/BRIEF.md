# Work Order: Isolate and Troubleshoot Container Network Namespace Routing

**Incident Ticket:** NET-40912  
**Target Host:** `lplab-05` (Ubuntu 24.04 LTS)  
**Assigned Student:** `sysadmin` (password: `linuxplus`)  

---

## Scenario Description

An isolated microservice running inside network namespace `app-ns` (`10.250.10.2:18090/health`) is completely unreachable from the root network namespace. System diagnostics show that virtual ethernet links are down, routes are missing, and packet filtering within the namespace is dropping incoming health checks.

Your task is to restore full network reachability between the root host namespace and the container microservice without removing the namespace or flushing host-wide firewall rules.

---

## Tasks & Acceptance Criteria

1. **Virtual Ethernet Interface Activation:**
   - Both `veth-host` (`10.250.10.1/24`) in the root namespace and `veth-app` (`10.250.10.2/24`) inside `app-ns` must be in the `UP` administrative and operational state.
   - The loopback interface (`lo`) inside `app-ns` must also be `UP`.

2. **Namespace Default Routing:**
   - Configure a default route inside `app-ns` pointing through the host peer gateway:
     ```bash
     ip netns exec app-ns ip route add default via 10.250.10.1
     ```

3. **Scoped Firewall Adjustment:**
   - The scoped nftables table `inet app_fw` inside `app-ns` must remain intact.
   - Modify or delete the drop rule inside `inet app_fw` so that TCP traffic to destination port `18090` is accepted.
   - *Safety Note:* Do NOT delete the entire table or flush rulesets in the root namespace. Only modify rules inside `app-ns`.

4. **Service Health & Verification:**
   - Ensure `netns-api.service` remains active under systemd.
   - Verify that running `curl -fsS --max-time 3 http://10.250.10.2:18090/health` from the root namespace returns HTTP `200` with JSON status `"healthy"`.

---

## Verification

Run verification in the desktop dashboard or via terminal:
```bash
lplab verify lab-05
```
