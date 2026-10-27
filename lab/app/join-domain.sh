#!/bin/bash
# Joins the app server to the northwind.internal domain, so staff sign in to it with their
# domain accounts and server rights follow their domain groups.
#
# Run on the app server, with the domain controller switched on. It asks for the domain
# Administrator password once:
#
#   ssh -t northwind-app 'sudo bash ~/lab/app/join-domain.sh'
#
# Only members of GG-IT may sign in to the server once it has joined.

set -euo pipefail

DC_IP=192.168.64.10
DOMAIN=northwind.internal
REALM=NORTHWIND.INTERNAL

step() { echo; echo "== $*"; }

if [ "$(id -u)" -ne 0 ]; then echo "Run this with sudo." >&2; exit 1; fi

step "Installing the domain join packages"
export DEBIAN_FRONTEND=noninteractive
echo "krb5-config krb5-config/default_realm string $REALM" | debconf-set-selections
apt-get update -qq
apt-get install -y -qq realmd sssd sssd-tools adcli libnss-sss libpam-sss krb5-user \
  samba-common-bin packagekit chrony >/dev/null

step "Using the domain controller for $DOMAIN names"
mkdir -p /etc/systemd/resolved.conf.d
cat > /etc/systemd/resolved.conf.d/northwind.conf <<EOF
[Resolve]
DNS=$DC_IP
Domains=$DOMAIN
EOF
systemctl restart systemd-resolved
if ! resolvectl query -t SRV "_ldap._tcp.$DOMAIN" >/dev/null 2>&1; then
  echo "The domain controller at $DC_IP is not answering DNS for $DOMAIN." >&2
  echo "Check it is switched on and that Samba's DNS server is running on it." >&2
  exit 1
fi
resolvectl query -t SRV "_ldap._tcp.$DOMAIN" | sed -n '1,2s/^/   /p'

step "Checking the clocks agree (Kerberos needs them within 5 minutes)"
systemctl enable --now chrony >/dev/null 2>&1 || true
chronyc -a makestep >/dev/null 2>&1 || true
echo "   app server: $(date -u +%H:%M:%S) UTC"

step "Joining $DOMAIN"
if realm list --name-only | grep -qx "$DOMAIN"; then
  echo "   already joined"
else
  realm discover "$DOMAIN" | sed -n '1,4s/^/   /p'
  realm join --verbose --user=Administrator "$DOMAIN"
fi

step "Sign in settings"
conf=/etc/sssd/sssd.conf
set_option() {  # set_option <key> <value>, in the domain section of sssd.conf
  if grep -q "^$1 *=" "$conf"; then
    sed -i "s|^$1 *=.*|$1 = $2|" "$conf"
  else
    sed -i "/^\[domain\/$DOMAIN\]/a $1 = $2" "$conf"
  fi
}
set_option use_fully_qualified_names False
set_option fallback_homedir /home/%u
set_option ad_gpo_access_control permissive
chmod 600 "$conf"
pam-auth-update --enable mkhomedir
realm deny --all
realm permit --groups GG-IT
systemctl restart sssd
sleep 3

step "Checking domain accounts work"
id ryan.patel
echo "   sign in allowed for: $(sed -n 's/^simple_allow_groups *= *//p' "$conf")"

step "JOINED $DOMAIN"
