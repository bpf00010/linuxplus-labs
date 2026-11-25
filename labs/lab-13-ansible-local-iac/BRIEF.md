# Work Order: Fix and Execute Ansible Local Playbook for Service Deployment

**Incident Ticket:** AUTO-83451  
**Target Host:** `lplab-13` (Ubuntu 24.04)  
**Assigned Student:** `sysadmin` (password: `linuxplus`)  

---

## Scenario Description

An Ansible project at `/srv/ansible-lab/` was created to automate the deployment of a `report-agent` service. The playbook `site.yml` and its Jinja2 template `templates/report-agent.conf.j2` contain multiple deliberate errors:

- YAML indentation errors in `site.yml`
- Wrong variable name referenced in the template task
- Mismatched handler name (case sensitivity)
- Uses `shell:` module where `template:` or `lineinfile` would be idempotent

The `report-agent.service` systemd unit is already installed but stopped and missing its configuration file.

---

## Tasks & Acceptance Criteria

1. **Fix the Ansible Playbook:**
   - Repair all YAML syntax and indentation errors in `/srv/ansible-lab/site.yml`.
   - Fix the template task to use the correct variable name and module.
   - Fix the handler name to match what the tasks notify.
   - Ensure all tasks use idempotent Ansible modules (no raw `shell:` for config management).

2. **Run the Playbook Successfully:**
   - Execute `ansible-playbook -i inventory.ini site.yml` from `/srv/ansible-lab/`.
   - The playbook must create user `reportsvc`, deploy `/etc/report-agent/agent.conf` with `MODE=production` and `PORT=18060`, and start/enable `report-agent.service`.

3. **Verify Idempotency:**
   - Running `ansible-playbook -i inventory.ini site.yml` a second time must report `changed=0` and `failed=0`.

---

## Verification

Run verification in the desktop dashboard or via terminal:
```bash
lplab verify lab-13
```
