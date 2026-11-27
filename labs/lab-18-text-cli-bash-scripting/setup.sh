#!/usr/bin/env bash
set -euo pipefail

mkdir -p /srv/data/files/sub /usr/local/bin
rm -f /srv/data/active_users.txt /usr/local/bin/check-file.sh

# 1. Populate /srv/data/users.csv (40 rows with duplicates and mixed active/disabled)
cat <<'EOF' > /srv/data/users.csv
username,department,status
alice,engineering,active
bob,ops,disabled
carol,security,active
dave,ops,active
alice,engineering,active
eve,finance,disabled
frank,engineering,active
grace,security,active
heidi,ops,disabled
ivan,engineering,active
judy,hr,active
kevin,ops,disabled
laura,security,active
mallory,finance,disabled
nathan,engineering,active
olivia,ops,active
carol,security,active
peggy,hr,disabled
quentin,engineering,active
rachel,ops,active
steve,security,disabled
trent,finance,active
ursula,engineering,active
victor,ops,disabled
wendy,security,active
xavier,hr,disabled
yvonne,engineering,active
zack,ops,active
dave,ops,active
frank,engineering,active
amber,ops,disabled
blake,security,active
chloe,engineering,active
derek,finance,disabled
elena,ops,active
felix,security,disabled
gina,hr,active
henry,engineering,disabled
iris,ops,active
ivan,engineering,active
EOF

# 2. Populate /srv/data/app.conf with old-db.internal
cat <<'EOF' > /srv/data/app.conf
[database]
primary_host=old-db.internal
replica_host=old-db.internal
connection_uri=postgres://old-db.internal:5432/appdb
port=5432
EOF

# 3. Populate /srv/data/files/ with mixed .log and .tmp files
dd if=/dev/zero of=/srv/data/files/cache1.tmp bs=1M count=2 status=none
dd if=/dev/zero of=/srv/data/files/sub/cache2.tmp bs=1M count=2 status=none
dd if=/dev/zero of=/srv/data/files/small1.tmp bs=1K count=10 status=none
dd if=/dev/zero of=/srv/data/files/sub/small2.tmp bs=1K count=50 status=none
dd if=/dev/zero of=/srv/data/files/app.log bs=1M count=2 status=none
echo "2026-11-26 ok" > /srv/data/files/sub/access.log

chown -R sysadmin:sysadmin /srv/data
