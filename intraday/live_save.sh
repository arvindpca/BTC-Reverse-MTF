#!/usr/bin/env bash
# Save the live paper state: commit the state folder and push it to the btc1h-paper-state branch.
set -u
cd "$1" || exit 1
git add -A
git commit -qm "BTC 1h live: ${2:-save} $(date -u +%FT%H:%MZ)" || exit 0
for i in 1 2 3; do git push -qf origin HEAD:refs/heads/btc1h-paper-state && exit 0; sleep 5; done
exit 1
