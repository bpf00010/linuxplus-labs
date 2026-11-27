# Lab 13: Fix Ansible Playbook and Service

**Distro:** Ubuntu 24.04 | **Login:** `sysadmin` / `linuxplus`
**Exam Focus:** Automation & Scripting, Services — Ansible YAML, template, handlers, idempotency

## Goal
The Ansible playbook `/srv/ansible-lab/site.yml` has a YAML indentation error, uses a non-idempotent `shell` task with a wrong variable, and has a handler name mismatch.

## Tasks
1. Fix YAML syntax, replace the `shell` config task with `ansible.builtin.template` using `templates/report-agent.conf.j2`, and match the handler name so `ansible-playbook -i inventory.ini --syntax-check site.yml` passes.
2. Run `ansible-playbook -i inventory.ini site.yml` to create user `reportsvc` and `/etc/report-agent/agent.conf` with `MODE=production` and `PORT=18060`.
3. Ensure `report-agent.service` is enabled and active.
4. Confirm a second `ansible-playbook -i inventory.ini site.yml` run exits 0 with `changed=0` and `failed=0`.
