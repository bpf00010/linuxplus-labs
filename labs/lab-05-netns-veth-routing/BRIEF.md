# Lab 05: Network Namespace Routing and Firewall

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Troubleshooting, Networking, Security — ip netns, veth, routes, nftables

## Goal
The API inside network namespace `app-ns` at `10.250.10.2:18090/health` is unreachable from the host because `veth-app` is down, the default route is missing, and `app_fw` drops port `18090`.

## Tasks
1. Bring up `veth-host` in the root namespace and `veth-app` inside namespace `app-ns`.
2. Add a default route `via 10.250.10.1` inside namespace `app-ns`.
3. Keep `netns-api.service` active and remove the TCP `18090` drop rule from `table inet app_fw` inside `app-ns`.
4. Confirm `curl -fsS http://10.250.10.2:18090/health` from the root namespace returns HTTP 200 with `"status":"healthy"`.

## Rules
- Do not delete `table inet app_fw` or flush firewall rules in the root namespace.
