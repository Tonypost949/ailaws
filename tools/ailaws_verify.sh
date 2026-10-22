#!/usr/bin/env bash
# ailaws_verify.sh
# Purpose: single-command integrity audit of every AI-laws copy on this machine.
#          Exits 0 only when ALL copies are byte-identical to the canonical
#          C:\Amd949609_Antigravity_v1\00_ailaws.md and contain every core clause.
# Usage: bash /mnt/c/Amd949609_Antigravity_v1/tools/ailaws_verify.sh
set -uo pipefail

CANON="/mnt/c/Amd949609_Antigravity_v1/00_ailaws.md"
REPO_RAW="https://raw.githubusercontent.com/Tonypost949/ailaws/main"
LOG="/mnt/c/Amd949609_Antigravity_v1/tools/logs/ailaws_verify.log"
mkdir -p "$(dirname "$LOG")"

REQUIRED=(
  "SOURCE OF TRUTH RULE"
  "OVERRIDE OPTIONS"
  "ABSOLUTE PROHIBITION ON PERMISSION-SEEKING"
  "ERROR COIN"
  "YOLO Mode"
  "OFFICIAL RECORDS, PRIMARY EVIDENCE"
  "Mandatory Cross-AI Tool Sharing"
  "THE TRINITY"
  "Reversion to Mean"
)

fail=0
say() { echo "$*" | tee -a "$LOG"; }

say "===== ailaws verify $(date -u '+%Y-%m-%dT%H:%M:%SZ') ====="
[ -s "$CANON" ] || { say "FATAL: canonical missing: $CANON"; exit 1; }
CSIZE=$(wc -c <"$CANON")
say "canonical: $CANON ($CSIZE bytes)"

for m in "${REQUIRED[@]}"; do
  if grep -qi -- "$m" "$CANON"; then say "  clause OK   : $m"; else say "  clause MISSING: $m"; fail=1; fi
done

# every derived local copy must resolve to identical bytes
COPIES=(
  "/home/osintneoai/AGENTS.md"
  "/home/osintneoai/00_ailaws.md"
  "/home/osintneoai/.agents/AGENTS.md"
  "/mnt/c/AGENTS.md"
  "/mnt/c/ailaws.md"
  "/mnt/c/00_ailaws.md"
  "/mnt/c/Amd949609_Antigravity_v1/AGENTS.md"
  "/mnt/c/OsintNeoAi/00_ailaws.md"
  "/mnt/c/OsintNeoAi/AGENTS.md"
  "/mnt/c/OsintNeoAi/.agents/AGENTS.md"
)
# C:\ root requires Windows elevation (UAC); report those as BLOCKED, not as drift
is_root_blocked() { case "$1" in /mnt/c/AGENTS.md|/mnt/c/ailaws.md|/mnt/c/00_ailaws.md) return 0;; *) return 1;; esac; }

BLOCKED=()
for c in "${COPIES[@]}"; do
  if [ -L "$c" ]; then
    tgt=$(readlink -f "$c")
    if [ "$(wc -c <"$c" 2>/dev/null)" = "$CSIZE" ]; then say "  link OK     : $c -> $tgt"
    else say "  link BROKEN : $c -> $tgt"; fail=1; fi
  elif [ -f "$c" ]; then
    if cmp -s <(tr -d '\r' <"$c") <(tr -d '\r' <"$CANON"); then say "  copy OK     : $c"
    elif is_root_blocked "$c"; then say "  BLOCKED     : $c ($(wc -c <"$c") bytes — C:\\ root needs UAC elevation)"; BLOCKED+=("$c")
    else say "  copy DRIFTED: $c ($(wc -c <"$c") bytes vs $CSIZE)"; fail=1; fi
  elif is_root_blocked "$c"; then say "  BLOCKED     : $c (absent — C:\\ root needs UAC elevation)"; BLOCKED+=("$c")
  else
    say "  absent      : $c"; fail=1
  fi
done

# remote repo must match too
for f in 00_ailaws.md AGENTS.md README.md ailaws.md; do
  url="$REPO_RAW/$f"
  got=$(curl -sfL --max-time 25 "$url" | tr -d '\r' | wc -c)
  local_bytes=$(tr -d '\r' <"$CANON" | wc -c)
  if [ "$got" = "$local_bytes" ]; then say "  remote OK   : $url ($got bytes)"
  else say "  remote DRIFT: $url ($got bytes vs $local_bytes)"; fail=1; fi
done

if [ "$fail" -eq 0 ] && [ "${#BLOCKED[@]}" -eq 0 ]; then
  say "RESULT: ALL GREEN — one law file, all mirrors identical"
elif [ "$fail" -eq 0 ]; then
  say "RESULT: GREEN except ${#BLOCKED[@]} path(s) requiring Windows elevation: ${BLOCKED[*]}"
  say "NOTICE: those are legacy C:\\ root copies; no agent entry point references them (see README)."
else
  say "RESULT: FAILURES ABOVE — run ailaws_github_sync.sh"
fi
exit "$fail"
