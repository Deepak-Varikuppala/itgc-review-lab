#!/bin/bash
# Builds the Northwind application server.
#
# Installs Gitea (where Northwind's developers keep and review code), the finance
# application, its deployment tool and the nightly backup job, then loads the change and
# backup history for Q3 2026. The server is left as it stood at the end of the quarter,
# including the changes that were made to it outside Northwind's own procedures.
#
# Run on the app server as root, after join-domain.sh:
#
#   sudo bash ~/lab/app/install.sh
#
# Safe to run again: anything already in place is left alone.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GITEA_VERSION=1.27.3
GITEA_URL=http://127.0.0.1:3000
GITEA_CONF=/etc/gitea/app.ini
GITEA_HOME=/var/lib/gitea
SECRETS=/root/northwind-lab
DATA=/var/lib/northwind
APP_DIR=/opt/northwind/finance-app
NW_LOG=/var/log/northwind

step() { echo; echo "== $*"; }
gitea_cli() { sudo -u git gitea --config "$GITEA_CONF" "$@"; }

wait_for_gitea() {
  for _ in $(seq 1 60); do
    if curl -fsS "$GITEA_URL/api/healthz" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  echo "Gitea did not start. See: journalctl -u gitea" >&2
  exit 1
}

if [ "$(id -u)" -ne 0 ]; then echo "Run this with sudo." >&2; exit 1; fi

step "Checking the server is joined to the domain"
if ! getent passwd ryan.patel >/dev/null; then
  echo "Domain accounts cannot be looked up. Run join-domain.sh first." >&2
  exit 1
fi
echo "   domain accounts resolve (ryan.patel is uid $(id -u ryan.patel))"

step "Installing packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git sqlite3 python3 curl ca-certificates chrony >/dev/null
mkdir -p "$SECRETS" && chmod 700 "$SECRETS"

step "Time synchronisation"
systemctl enable --now chrony >/dev/null 2>&1 || true
chronyc -n tracking | sed -n 's/^\(Reference ID\|System time\) *: /   /p' || true

step "Gitea $GITEA_VERSION"
case "$(dpkg --print-architecture)" in
  arm64) arch=arm64 ;;
  amd64) arch=amd64 ;;
  *) echo "Unsupported architecture" >&2; exit 1 ;;
esac
if ! gitea --version 2>/dev/null | grep -q "version $GITEA_VERSION "; then
  base="https://github.com/go-gitea/gitea/releases/download/v$GITEA_VERSION"
  tmp="$(mktemp -d)"
  curl -fsSL -o "$tmp/gitea-$GITEA_VERSION-linux-$arch" "$base/gitea-$GITEA_VERSION-linux-$arch"
  curl -fsSL -o "$tmp/gitea.sha256" "$base/gitea-$GITEA_VERSION-linux-$arch.sha256"
  (cd "$tmp" && sha256sum -c gitea.sha256)
  install -m 755 "$tmp/gitea-$GITEA_VERSION-linux-$arch" /usr/local/bin/gitea
  rm -rf "$tmp"
fi
if ! id git >/dev/null 2>&1; then
  adduser --system --shell /bin/bash --gecos 'Gitea' --group --disabled-password \
    --home /home/git git >/dev/null
fi
install -d -o git -g git -m 750 "$GITEA_HOME" "$GITEA_HOME/custom" "$GITEA_HOME/data" "$GITEA_HOME/log"
install -d -o root -g git -m 770 /etc/gitea
if [ ! -f "$GITEA_CONF" ]; then
  host_ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i < NF; i++) if ($i == "src") print $(i + 1)}' || true)"
  host_ip="${host_ip:-127.0.0.1}"
  cat > "$GITEA_CONF" <<EOF
APP_NAME = Northwind Code
RUN_USER = git
RUN_MODE = prod
WORK_PATH = $GITEA_HOME

[server]
PROTOCOL = http
HTTP_ADDR = 0.0.0.0
HTTP_PORT = 3000
DOMAIN = $host_ip
ROOT_URL = http://$host_ip:3000/
DISABLE_SSH = true
LFS_START_SERVER = false
OFFLINE_MODE = true

[database]
DB_TYPE = sqlite3
PATH = $GITEA_HOME/data/gitea.db

[repository]
ROOT = $GITEA_HOME/data/gitea-repositories
DEFAULT_BRANCH = main

[security]
INSTALL_LOCK = true
SECRET_KEY = $(sudo -u git gitea generate secret SECRET_KEY)
INTERNAL_TOKEN = $(sudo -u git gitea generate secret INTERNAL_TOKEN)
MIN_PASSWORD_LENGTH = 12

[oauth2]
JWT_SECRET = $(sudo -u git gitea generate secret JWT_SECRET)

[service]
DISABLE_REGISTRATION = true
REQUIRE_SIGNIN_VIEW = true
DEFAULT_ALLOW_CREATE_ORGANIZATION = false

[actions]
ENABLED = false

[session]
PROVIDER = file

[log]
MODE = file
LEVEL = Info
ROOT_PATH = $GITEA_HOME/log

[cron.update_checker]
ENABLED = false
EOF
  chown root:git "$GITEA_CONF"
  chmod 660 "$GITEA_CONF"
fi
cat > /etc/systemd/system/gitea.service <<EOF
[Unit]
Description=Gitea, Northwind's code repository
After=network-online.target
Wants=network-online.target

[Service]
User=git
Group=git
WorkingDirectory=$GITEA_HOME
ExecStart=/usr/local/bin/gitea web --config $GITEA_CONF
Environment=USER=git HOME=/home/git GITEA_WORK_DIR=$GITEA_HOME
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
gitea_cli migrate >/dev/null 2>&1 || { echo "Gitea could not set up its database" >&2; exit 1; }
systemctl enable --now gitea >/dev/null 2>&1
wait_for_gitea
if ! gitea_cli admin user list --admin | awk '{print $2}' | grep -qx gitea-admin; then
  pw="$(openssl rand -base64 18)"
  gitea_cli admin user create --username gitea-admin --email gitea-admin@northwind.internal \
    --fullname "Gitea administrator" --password "$pw" --admin --must-change-password=false >/dev/null
  echo "gitea-admin,$pw" >> "$SECRETS/gitea-passwords.csv"
  chmod 600 "$SECRETS/gitea-passwords.csv"
fi
echo "   Gitea is running at $(awk -F' = ' '/^ROOT_URL/{print $2}' "$GITEA_CONF")"

step "Finance database"
if ! id financeapp >/dev/null 2>&1; then
  adduser --system --group --no-create-home --home /nonexistent financeapp >/dev/null
fi
install -d -o root -g financeapp -m 750 "$DATA"
python3 "$HERE/files/seed_finance.py" "$DATA/finance.db"
chown root:financeapp "$DATA/finance.db"
chmod 640 "$DATA/finance.db"

step "Change history"
install -d -m 755 "$NW_LOG"
if [ ! -f "$SECRETS/build-state.json" ]; then
  token="$(gitea_cli admin user generate-access-token --username gitea-admin \
    --token-name "history-build-$(date +%s)" --scopes all --raw | tail -n 1)"
  umask 077
  echo "$token" > "$SECRETS/gitea-admin-token"
  umask 022
  python3 "$HERE/build_repo.py" build --gitea "$GITEA_URL" \
    --token-file "$SECRETS/gitea-admin-token" \
    --gitea-cmd "sudo -u git gitea --config $GITEA_CONF"
  rm -f "$SECRETS/gitea-admin-token"
  systemctl stop gitea
  sudo -u git cp "$GITEA_HOME/data/gitea.db" "$GITEA_HOME/data/gitea.db.before-dates"
  python3 "$HERE/build_repo.py" backdate --db "$GITEA_HOME/data/gitea.db"
  rm -f "$GITEA_HOME/data/gitea.db.before-dates"
  systemctl start gitea
  wait_for_gitea
fi
if [ ! -f "$NW_LOG/deployments.log" ]; then
  python3 "$HERE/build_repo.py" deploylog --out "$NW_LOG/deployments.log" > "$SECRETS/production-commit"
fi
echo "   $(wc -l < "$NW_LOG/deployments.log") deployments in $NW_LOG/deployments.log"

step "Production deployment of the finance application"
if [ ! -d "$APP_DIR/.git" ]; then
  token="$(gitea_cli admin user generate-access-token --username svc-deploy \
    --token-name production-deploy --scopes read:repository --raw | tail -n 1)"
  umask 077
  printf 'http://svc-deploy:%s@127.0.0.1%%3a3000\n' "$token" > /root/.git-credentials
  umask 022
  git config --global credential.helper store
  install -d -m 755 /opt/northwind
  git clone --quiet "$GITEA_URL/northwind/finance-app.git" "$APP_DIR"
  git -C "$APP_DIR" checkout --quiet --detach "$(cat "$SECRETS/production-commit")"
fi
cat > /etc/systemd/system/finance-app.service <<EOF
[Unit]
Description=Northwind finance application
After=network-online.target

[Service]
User=financeapp
Group=financeapp
Environment=FINANCE_DB=$DATA/finance.db PORT=8080
ExecStart=/usr/bin/python3 $APP_DIR/app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable finance-app >/dev/null 2>&1
systemctl restart finance-app
install -m 755 "$HERE/files/northwind-deploy" /usr/local/sbin/northwind-deploy
cat > /etc/sudoers.d/northwind <<'EOF'
# Northwind application server
# IT server administrators have full administrator rights.
%it-server-admins ALL=(ALL:ALL) ALL
# Change deployers may run the deployment tool, and nothing else, as root.
%change-deployers ALL=(root) /usr/local/sbin/northwind-deploy
EOF
chmod 440 /etc/sudoers.d/northwind
visudo -cqf /etc/sudoers.d/northwind
for _ in $(seq 1 20); do
  curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1 && break
  sleep 1
done
echo "   finance app version $(git -C "$APP_DIR" show HEAD:VERSION) is running on port 8080"

step "Nightly backup"
install -m 755 "$HERE/files/northwind-backup" /usr/local/sbin/northwind-backup
install -d -m 750 /var/backups/northwind
cat > /etc/cron.d/northwind-backup <<'EOF'
# Nightly backup of the finance database (owner: aisha.khan)
SHELL=/bin/bash
30 1 * * * root /usr/local/sbin/northwind-backup
EOF
chmod 644 /etc/cron.d/northwind-backup
if [ ! -f "$NW_LOG/backup.log" ]; then
  cp "$HERE/data/backup-history.log" "$NW_LOG/backup.log"
  /usr/local/sbin/northwind-backup
fi
echo "   last run: $(tail -n 1 "$NW_LOG/backup.log")"

step "Changes made to the server outside the change process"
# A local account set up for the supplier's support engineer in August, given
# administrator rights, and never removed.
if ! id support >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash --comment "DevPartners support engineer" support
  usermod -aG sudo support
  echo "support:$(openssl rand -base64 15)" | chpasswd
  chage -d 2026-08-12 support
  touch -d 2026-08-12T10:05:00Z /home/support
fi
# Rights added for an emergency fix on 23 September and not taken away afterwards.
if [ ! -f /etc/sudoers.d/ryan-emergency ]; then
  cat > /etc/sudoers.d/ryan-emergency <<'EOF'
# Temporary, for the approvals page fix (23/09)
ryan.patel ALL=(ALL) NOPASSWD: ALL
EOF
  chmod 440 /etc/sudoers.d/ryan-emergency
  visudo -cqf /etc/sudoers.d/ryan-emergency
  touch -d 2026-09-23T20:41:00Z /etc/sudoers.d/ryan-emergency
fi
# A job a developer scheduled to tidy old payment exports. It runs his own script as root.
if [ ! -f /etc/cron.d/finance-tidy ]; then
  group="$(id -gn ryan.patel)"
  install -d -o ryan.patel -g "$group" -m 755 /home/ryan.patel /home/ryan.patel/bin
  install -d -m 750 -o root -g financeapp "$DATA/exports"
  cat > /home/ryan.patel/bin/tidy-exports.sh <<'EOF'
#!/bin/bash
# Removes payment export files more than 7 days old.
find /var/lib/northwind/exports -name '*.csv' -mtime +7 -delete
EOF
  chown ryan.patel:"$group" /home/ryan.patel/bin/tidy-exports.sh
  chmod 755 /home/ryan.patel/bin/tidy-exports.sh
  cat > /etc/cron.d/finance-tidy <<'EOF'
15 2 * * * root /home/ryan.patel/bin/tidy-exports.sh
EOF
  chmod 644 /etc/cron.d/finance-tidy
  touch -d 2026-07-02T16:12:00Z /home/ryan.patel/bin/tidy-exports.sh /etc/cron.d/finance-tidy
fi

step "APP SERVER READY"
echo "   Gitea:       $(awk -F' = ' '/^ROOT_URL/{print $2}' "$GITEA_CONF")"
echo "   Finance app: http://$(awk -F' = ' '/^DOMAIN/{print $2}' "$GITEA_CONF"):8080/"
echo "   Passwords:   $SECRETS/gitea-passwords.csv (root only)"
