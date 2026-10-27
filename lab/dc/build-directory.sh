#!/bin/bash
# Builds the Northwind Retail user directory on the Samba domain controller.
#
# Creates the organisational structure, groups, staff, admin, shared and service
# accounts from staff.csv, applies the domain password policy, and then signs in
# as the active accounts so the directory has realistic last logon dates.
#
# The directory deliberately contains control weaknesses for the ITGC review to
# find. Safe to run more than once: anything that already exists is left alone.
#
# Run on the domain controller:  sudo ./build-directory.sh

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAFF_CSV="${STAFF_CSV:-$HERE/staff.csv}"
SAMBA_TOOL="${SAMBA_TOOL:-samba-tool}"
SAM_LDB="${SAM_LDB:-/var/lib/samba/private/sam.ldb}"
PASSWORD_FILE="${PASSWORD_FILE:-/root/northwind-lab/account-passwords.csv}"
LOGON_SERVER="${LOGON_SERVER:-127.0.0.1}"
NETBIOS="NORTHWIND"
BASE_DN="DC=northwind,DC=internal"
COMPANY="Northwind Retail"

CONF=()
if [ -n "${SMB_CONF:-}" ]; then CONF=(-s "$SMB_CONF"); fi
st() { $SAMBA_TOOL "$@" "${CONF[@]}"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this with sudo." >&2
  exit 1
fi
[ -f "$STAFF_CSV" ] || { echo "Cannot find $STAFF_CSV" >&2; exit 1; }

ou_path() {
  case "$1" in
    Finance|IT|HR|Sales|Operations) echo "OU=$1,OU=Staff,OU=Northwind" ;;
    Leavers|Admins|ServiceAccounts|Groups) echo "OU=$1,OU=Northwind" ;;
    *) echo "Unknown OU '$1' in staff.csv" >&2; exit 1 ;;
  esac
}

new_password() {
  python3 -c 'import secrets,string
a=string.ascii_letters+string.digits
print("Nw" + "".join(secrets.choice(a) for _ in range(16)) + "k7")'
}

echo "== 1. Organisational units"
for ou in "OU=Northwind" "OU=Staff,OU=Northwind" \
          "OU=Finance,OU=Staff,OU=Northwind" "OU=IT,OU=Staff,OU=Northwind" \
          "OU=HR,OU=Staff,OU=Northwind" "OU=Sales,OU=Staff,OU=Northwind" \
          "OU=Operations,OU=Staff,OU=Northwind" "OU=Leavers,OU=Northwind" \
          "OU=Admins,OU=Northwind" "OU=ServiceAccounts,OU=Northwind" "OU=Groups,OU=Northwind"; do
  existing_ous="$(st ou list --full-dn 2>/dev/null || true)"
  if grep -qix "$ou,$BASE_DN" <<< "$existing_ous"; then
    echo "   exists   $ou"
  else
    st ou create "$ou" >/dev/null
    echo "   created  $ou"
  fi
done

echo "== 2. Groups"
while IFS='|' read -r group description; do
  if st group show "$group" >/dev/null 2>&1; then
    echo "   exists   $group"
  else
    st group add "$group" --groupou="OU=Groups,OU=Northwind" --description="$description" >/dev/null
    echo "   created  $group"
  fi
done <<'GROUPS'
GG-Finance|All Finance department staff
GG-IT|All IT department staff
GG-HR|All HR department staff
GG-Sales|All Sales department staff
GG-Operations|All Operations department staff
Finance-Payments-Initiators|Can create supplier payments in the finance application
Finance-Payments-Approvers|Can approve supplier payments in the finance application
IT-Server-Admins|Administrator access to company servers
Change-Approvers|Can approve changes to production systems
Change-Deployers|Can deploy changes to production systems
Developers|Software developers
Helpdesk|IT helpdesk: can reset user passwords
GROUPS

echo "== 3. Accounts"
mkdir -p "$(dirname "$PASSWORD_FILE")"
touch "$PASSWORD_FILE"
chmod 600 "$PASSWORD_FILE"

declare -A USER_OU
while IFS=, read -r username _ _ _ _ _ _ ou _ _; do
  [ "$username" = "username" ] && continue
  USER_OU[$username]="$(ou_path "$ou")"
done < "$STAFF_CSV"

while IFS=, read -r username given surname employee_id department title manager ou groups flags; do
  [ "$username" = "username" ] && continue
  user_ou="$(ou_path "$ou")"

  password="$(grep -m1 "^$username," "$PASSWORD_FILE" | cut -d, -f2 || true)"
  if [ -z "$password" ]; then
    password="$(new_password)"
    echo "$username,$password" >> "$PASSWORD_FILE"
  fi

  if st user show "$username" >/dev/null 2>&1; then
    echo "   exists   $username"
  else
    st user create "$username" "$password" --use-username-as-cn \
      --given-name="$given" --surname="$surname" --job-title="$title" \
      --department="$department" --company="$COMPANY" --description="$title" \
      --mail-address="$username@northwind.internal" --userou="$user_ou" \
      > /dev/null 2> >(grep -v "Using passwords on command line" >&2)

    dn="CN=$username,$user_ou,$BASE_DN"
    {
      echo "dn: $dn"
      echo "changetype: modify"
      if [ -n "$employee_id" ]; then
        echo "replace: employeeID"
        echo "employeeID: $employee_id"
        echo "-"
      fi
      if [ -n "$manager" ]; then
        echo "replace: manager"
        echo "manager: CN=$manager,${USER_OU[$manager]},$BASE_DN"
        echo "-"
      fi
    } > /tmp/northwind-attrs.ldif
    if grep -q "^replace" /tmp/northwind-attrs.ldif; then
      ldbmodify -H "$SAM_LDB" /tmp/northwind-attrs.ldif >/dev/null
    fi
    rm -f /tmp/northwind-attrs.ldif

    [[ ";$flags;" == *";pwnoexpire;"* ]] && st user setexpiry "$username" --noexpiry >/dev/null
    [[ ";$flags;" == *";disabled;"* ]] && st user disable "$username" >/dev/null
    echo "   created  $username"
  fi

  IFS=';' read -ra group_list <<< "$groups"
  for group in "${group_list[@]}"; do
    [ -z "$group" ] && continue
    members="$(st group listmembers "$group" 2>/dev/null || true)"
    if ! grep -qx "$username" <<< "$members"; then
      st group addmembers "$group" "$username" >/dev/null
    fi
  done
done < "$STAFF_CSV"

echo "== 4. Domain password policy"
st domain passwordsettings set --complexity=on --min-pwd-length=8 \
  --history-length=24 --max-pwd-age=42 --min-pwd-age=1 \
  --account-lockout-threshold=0 >/dev/null
st domain passwordsettings show | sed 's/^/   /'

echo "== 5. Sign in as active accounts (sets realistic last logon dates)"
if [ "${SKIP_LOGONS:-0}" = "1" ]; then
  echo "   skipped"
else
  signed_in=0
  while IFS=, read -r username _ _ _ _ _ _ _ _ flags; do
    [ "$username" = "username" ] && continue
    [[ ";$flags;" == *";nologon;"* ]] && continue
    password="$(grep -m1 "^$username," "$PASSWORD_FILE" | cut -d, -f2)"
    if smbclient "//$LOGON_SERVER/netlogon" -U "$NETBIOS\\$username%$password" -c "ls" \
         >/dev/null 2>&1; then
      signed_in=$((signed_in + 1))
    else
      echo "   could not sign in as $username"
    fi
  done < "$STAFF_CSV"
  echo "   signed in as $signed_in accounts"
fi

echo "== 6. Summary"
echo "   Users:  $(st user list | wc -l) (including built in accounts)"
echo "   Groups in Northwind OU: $(st group list --full-dn | grep -c 'OU=Groups,OU=Northwind')"
echo "   Domain Admins: $(st group listmembers 'Domain Admins' | sort | tr '\n' ' ')"
echo "   Account passwords are stored in $PASSWORD_FILE (readable by root only)"
echo "== DIRECTORY BUILD FINISHED"
