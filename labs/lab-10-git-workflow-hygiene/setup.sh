#!/usr/bin/env bash
set -euo pipefail

# Create sysadmin user if not present
id -u sysadmin &>/dev/null || useradd -m -s /bin/bash sysadmin
echo "sysadmin:linuxplus" | chpasswd

# 1. Create the ops-scripts repository
mkdir -p /srv/ops-scripts
chown sysadmin:sysadmin /srv/ops-scripts
cd /srv/ops-scripts

sudo -u sysadmin git init --initial-branch=main
sudo -u sysadmin git config user.name "Ops Team"
sudo -u sysadmin git config user.email "ops@lab.internal"

# Create initial files on main
cat > config.env <<'CONF'
# Operations Configuration
APP_NAME=ops-monitor
LOG_LEVEL=info
TIMEOUT=30
RETRIES=3
CONF

cat > deploy.sh <<'DEPLOY'
#!/usr/bin/env bash
set -euo pipefail
echo "Deploying application..."
source ./config.env
echo "Using timeout: $TIMEOUT"
DEPLOY
chmod +x deploy.sh

# Accidentally commit a secrets file
cat > .env.secrets <<'SECRETS'
DB_PASSWORD=supersecret123
API_TOKEN=tok_abc987xyz
AWS_SECRET_KEY=AKIA1234567890EXAMPLE
SECRETS

chown sysadmin:sysadmin config.env deploy.sh .env.secrets

sudo -u sysadmin git add config.env deploy.sh .env.secrets
sudo -u sysadmin git commit -m "Initial commit: config, deploy script, and secrets"

# 2. Create feature branch with conflicting change
sudo -u sysadmin git checkout -b feature/alert-fix

cat > config.env <<'CONF'
# Operations Configuration
APP_NAME=ops-monitor
LOG_LEVEL=info
TIMEOUT=60
RETRIES=5
CONF
chown sysadmin:sysadmin config.env

cat > alert.sh <<'ALERT'
#!/usr/bin/env bash
set -euo pipefail
echo "Alert system check..."
source ./config.env
echo "Timeout set to: $TIMEOUT"
ALERT
chmod +x alert.sh
chown sysadmin:sysadmin alert.sh

sudo -u sysadmin git add config.env alert.sh
sudo -u sysadmin git commit -m "feature: update timeout to 60 and add alert script"

# 3. Go back to main and make a conflicting change
sudo -u sysadmin git checkout main

cat > config.env <<'CONF'
# Operations Configuration
APP_NAME=ops-monitor
LOG_LEVEL=warn
TIMEOUT=30
RETRIES=3
CONF
chown sysadmin:sysadmin config.env

sudo -u sysadmin git add config.env
sudo -u sysadmin git commit -m "main: change log level to warn"

# 4. Create a broken pre-commit hook
mkdir -p .git/hooks
cat > .git/hooks/pre-commit <<'HOOK'
#!/usr/bin/env bash
# Pre-commit hook: validate staged .sh files
set -euo pipefail

staged=$(git diff --cached --name-only --diff-filter=ACM | grep '\.sh$' || true

if [ -n "$staged" ]; then
    for f in $staged; do
        bash -n "$f"
        if [ $? -ne 0 ]; then
            echo "Syntax error in $f"
            exit 1
        fi
    done
fi
HOOK
# Intentionally NOT making it executable
chmod 644 .git/hooks/pre-commit
chown -R sysadmin:sysadmin /srv/ops-scripts
