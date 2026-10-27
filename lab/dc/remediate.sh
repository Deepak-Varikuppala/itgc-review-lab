#!/bin/bash
# Applies the agreed remediation for the Q3 2026 logical access findings.
#
# Each action is labelled with the finding it resolves. Run on the domain controller
# after the review, then extract fresh evidence and rerun the tests to confirm.
#
#   sudo bash remediate.sh

set -euo pipefail

SAMBA_TOOL="${SAMBA_TOOL:-samba-tool}"
SAM_LDB="${SAM_LDB:-/var/lib/samba/private/sam.ldb}"
BASE_DN="DC=northwind,DC=internal"
CONF=()
if [ -n "${SMB_CONF:-}" ]; then CONF=(-s "$SMB_CONF"); fi
st() { $SAMBA_TOOL "$@" "${CONF[@]}"; }

if [ "$(id -u)" -ne 0 ]; then echo "Run this with sudo." >&2; exit 1; fi

remove_from() {  # remove_from <group> <user>
  local members
  members="$(st group listmembers "$1" 2>/dev/null || true)"
  if grep -qx "$2" <<< "$members"; then
    st group removemembers "$1" "$2" >/dev/null
    echo "   removed $2 from $1"
  fi
}

remove_all_groups() {  # remove_all_groups <user>
  local group
  while read -r group; do
    [ -z "$group" ] && continue
    [ "$group" = "Domain Users" ] && continue
    remove_from "$group" "$1"
  done < <(st group list)
}

disable() {
  local uac
  uac="$(st user show "$1" | awk '/^userAccountControl: /{print $2}')"
  if (( (uac & 0x2) == 0 )); then
    st user disable "$1" >/dev/null
    echo "   disabled $1"
  fi
}

move_to_leavers() {
  if ! st user show "$1" 2>/dev/null | grep -q "^dn: CN=$1,OU=Leavers,"; then
    st user move "$1" "OU=Leavers,OU=Northwind" >/dev/null
    echo "   moved $1 to Leavers"
  fi
}

clear_never_expires() {  # Clears the 'password never expires' flag (0x10000).
  local dn uac
  dn="$(st user show "$1" | awk '/^dn: /{print substr($0,5)}')"
  uac="$(st user show "$1" | awk '/^userAccountControl: /{print $2}')"
  if (( uac & 0x10000 )); then
    printf "dn: %s\nchangetype: modify\nreplace: userAccountControl\nuserAccountControl: %d\n" \
      "$dn" $(( uac & ~0x10000 )) | ldbmodify -H "$SAM_LDB" >/dev/null
    echo "   cleared 'password never expires' on $1"
  fi
}

echo "== F1 Leaver mark.taylor"
disable mark.taylor; remove_all_groups mark.taylor; move_to_leavers mark.taylor

echo "== F2 Domain Admins"
remove_from "Domain Admins" liam.brooks
remove_from "Domain Admins" svc-backup
members="$(st group listmembers "Backup Operators" 2>/dev/null || true)"
if ! grep -qx svc-backup <<< "$members"; then
  st group addmembers "Backup Operators" svc-backup >/dev/null
  echo "   added svc-backup to Backup Operators (the rights the backup job needs)"
fi

echo "== F3 Shared account finance.shared"
disable finance.shared; remove_all_groups finance.shared

echo "== F4 Mover emma.wilson"
remove_from Finance-Payments-Initiators emma.wilson
remove_from GG-Finance emma.wilson

echo "== F5 Contractor leo.martin"
disable leo.martin; remove_all_groups leo.martin; move_to_leavers leo.martin

echo "== F6 Password and lockout policy"
st domain passwordsettings set --min-pwd-length=12 --account-lockout-threshold=5 \
  --account-lockout-duration=30 --reset-account-lockout-after=30 >/dev/null
echo "   minimum length 12, lockout after 5 attempts for 30 minutes"

echo "== F7 Non-expiring passwords"
clear_never_expires sarah.mitchell
clear_never_expires finance.shared

echo "== F8 Payments segregation of duties"
remove_from Finance-Payments-Approvers priya.shah

echo "== F9 Unused service account"
disable svc-financeapp

echo "== F10 Quarterly access review"
echo "   process change: no directory change (first review due Q4 2026)"

echo "== REMEDIATION FINISHED"
