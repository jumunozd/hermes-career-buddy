#!/bin/bash
# Daily encrypted backup of Hermes Career Buddy (private/ + Baserow). Silent on success; a failure exits non-zero
# so Hermes cron sends the failure notice to Telegram.
cd "${HCB_ROOT:-$HOME/Desktop/Hermes Career Buddy}" || exit 1   # set HCB_ROOT on the VPS
out=$(bin/hcb backup 2>&1) || { echo "Respaldo de Career Buddy FALLÓ:"; echo "$out" | tail -5; exit 1; }
