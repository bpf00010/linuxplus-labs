#!/usr/bin/env bash
set -euo pipefail

# Create sysadmin user if not present
id -u sysadmin &>/dev/null || useradd -m -s /bin/bash sysadmin
echo "sysadmin:linuxplus" | chpasswd
usermod -aG sudo sysadmin 2>/dev/null || true

# 1. Create the Ansible project directory
mkdir -p /srv/ansible-lab/templates
chown -R sysadmin:sysadmin /srv/ansible-lab

# 2. Create inventory
cat > /srv/ansible-lab/inventory.ini <<'INV'
[local]
localhost ansible_connection=local
INV

# 3. Create the Jinja2 template (correct template, playbook references wrong var)
cat > /srv/ansible-lab/templates/report-agent.conf.j2 <<'J2'
# Report Agent Configuration
# Managed by Ansible - do not edit manually
MODE={{ agent_mode }}
PORT={{ agent_port }}
LOG_DIR=/var/log/report-agent
USER={{ agent_user }}
J2

# 4. Create BROKEN site.yml with multiple deliberate errors
cat > /srv/ansible-lab/site.yml <<'PLAYBOOK'
---
- name: Deploy report-agent service
  hosts: local
  become: true
  vars:
    agent_mode: production
    agent_port: 18060
    agent_user: reportsvc

  tasks:
    - name: Create service user
      ansible.builtin.user:
        name: "{{ agent_user }}"
        system: true
        shell: /usr/sbin/nologin
         create_home: false

    - name: Create configuration directory
      ansible.builtin.file:
        path: /etc/report-agent
        state: directory
        owner: "{{ agent_user }}"
        mode: "0755"

    - name: Deploy agent configuration
      ansible.builtin.shell: |
        cat > /etc/report-agent/agent.conf <<CONF
        MODE={{ service_mode }}
        PORT={{ agent_port }}
        LOG_DIR=/var/log/report-agent
        USER={{ agent_user }}
        CONF
      notify: Restart report-agent

    - name: Ensure report-agent service is enabled and started
      ansible.builtin.systemd:
        name: report-agent
        enabled: true
        state: started
        daemon_reload: true

  handlers:
    - name: restart report-agent
      ansible.builtin.systemd:
        name: report-agent
        state: restarted
        daemon_reload: true
PLAYBOOK

# 5. Install the report-agent systemd unit
cat > /etc/systemd/system/report-agent.service <<'UNIT'
[Unit]
Description=Report Agent Service
After=network.target

[Service]
Type=simple
User=root
EnvironmentFile=/etc/report-agent/agent.conf
ExecStart=/bin/sh -c 'echo "report-agent running MODE=$MODE PORT=$PORT"; while true; do sleep 60; done'
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload 2>/dev/null || true
systemctl stop report-agent.service 2>/dev/null || true
systemctl disable report-agent.service 2>/dev/null || true

# Ensure config directory does NOT exist yet
rm -rf /etc/report-agent

chown -R sysadmin:sysadmin /srv/ansible-lab
