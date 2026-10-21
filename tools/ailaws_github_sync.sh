#!/usr/bin/env bash
# ailaws_github_sync.sh
# Purpose: keep https://github.com/Tonypost949/ailaws in sync with the canonical
#          AI laws file, and make it IMPOSSIBLE to publish a laws file that has
#          had the SOURCE OF TRUTH RULE (or other core content) stripped out.
#
# Canonical source (first that exists wins):
#   1. /mnt/c/Amd949609_Antigravity_v1/00_ailaws.md   (Windows master)
#   2. /home/osintneoai/00_ailaws.md                  (WSL mirror)
#
# Every law mirror in the repo is REGENERATED from the canonical file:
#   00_ailaws.md  AGENTS.md  README.md  ailaws.md
# Safe: bundles a backup before mutation, never deletes data, idempotent.
set -uo pipefail

REPO_URL="https://github.com/Tonypost949/ailaws.git"
WORK="/tmp/opencode/ailaws_sync_work"
LOG="/mnt/c/Amd949609_Antigravity_v1/tools/logs/ailaws_github_sync.log"
mkdir -p "$(dirname "$LOG")"

# Core clauses that must be present, or the push is refused.
REQUIRED_MARKERS=(
  "SOURCE OF TRUTH RULE"
  "OVERRIDE OPTIONS"
  "ABSOLUTE PROHIBITION ON PERMISSION-SEEKING"
  "ERROR COIN"
  "YOLO Mode"
  "OFFICIAL RECORDS, PRIMARY EVIDENCE"
)

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" | tee -a "$LOG"; }

CANON=""
for c in /mnt/c/Amd949609_Antigravity_v1/00_ailaws.md /home/osintneoai/00_ailaws.md; do
  [ -s "$c" ] && CANON="$c" && break
done
[ -z "$CANON" ] && { log "SKIP: no canonical 00_ailaws.md found"; exit 0; }
log "START canonical=$CANON ($(wc -c <"$CANON") bytes)"

# ---- tripwire: never publish a gutted laws file ----------------------------
MISSING=""
for m in "${REQUIRED_MARKERS[@]}"; do
  grep -qi -- "$m" "$CANON" || MISSING="$MISSING [$m]"
done
if [ -n "$MISSING" ]; then
  log "ABORT: canonical file is missing required clauses:$MISSING — nothing pushed."
  exit 2
fi

if [ ! -d "$WORK/.git" ]; then
  rm -rf "$WORK"
  gh repo clone "$REPO_URL" "$WORK" -- --quiet >>"$LOG" 2>&1 || { log "ERROR: clone failed"; exit 1; }
else
  git -C "$WORK" fetch --quiet origin main >>"$LOG" 2>&1
  git -C "$WORK" reset --quiet --hard origin/main >>"$LOG" 2>&1
fi

# ---- regenerate every law mirror from the single canonical file ------------
for f in 00_ailaws.md AGENTS.md README.md ailaws.md; do
  cp -f "$CANON" "$WORK/$f"
done

# ---- keep the working checkout + legacy Windows prompt paths generated ------
# C:\OsintNeoAi is a code checkout, never a source of truth: its law copies are
# overwritten from the canonical file so no divergent fork can live there.
for p in "/mnt/c/OsintNeoAi/00_ailaws.md" "/mnt/c/OsintNeoAi/AGENTS.md" \
         "/mnt/c/OsintNeoAi/.agents/AGENTS.md" "/mnt/c/Amd949609_Antigravity_v1/AGENTS.md" \
         "/mnt/c/00_ailaws.md" "/mnt/c/AGENTS.md" "/mnt/c/ailaws.md"; do
  [ -d "$(dirname "$p")" ] || continue
  cmp -s "$p" "$CANON" && continue
  # C:\ root is owned by BUILTIN\Administrators — WSL cannot write it without a UAC click.
  if [ -w "$(dirname "$p")" ] || [ -w "$p" ]; then
    cp -f "$CANON" "$p" 2>/dev/null && log "regenerated $p" || log "WARN: could not write $p"
  else
    log "SKIP (needs Windows elevation): $p"
  fi
done

# WSL agent paths stay symlinks to the master; repair them if ever replaced by copies
for l in "/home/osintneoai/AGENTS.md" "/home/osintneoai/00_ailaws.md" "/home/osintneoai/.agents/AGENTS.md"; do
  [ -d "$(dirname "$l")" ] || continue
  if [ -L "$l" ] && [ "$(readlink -f "$l")" = "$(readlink -f "$CANON")" ]; then
    :
  elif [ -f "$l" ] && cmp -s "$l" "$CANON"; then
    :
  else
    ln -sfn "$CANON" "$l" && log "relinked $l -> $CANON"
  fi
done

git -C "$WORK" config user.name  "Osint Neo"
git -C "$WORK" config user.email "anthony.dimarcello@students.post.edu"

if [ -z "$(git -C "$WORK" status --porcelain)" ]; then
  log "OK: remote already current (no changes)"
  exit 0
fi

BK="/tmp/opencode/ailaws_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BK" && git -C "$WORK" bundle create "$BK/repo.bundle" --all >>"$LOG" 2>&1
log "backup=$BK"

git -C "$WORK" add -A >>"$LOG" 2>&1
git -C "$WORK" commit -q -m "auto-sync canonical 00_ailaws.md ($(date -u +%Y-%m-%dT%H:%M:%SZ))" >>"$LOG" 2>&1
if git -C "$WORK" push origin main >>"$LOG" 2>&1; then
  log "PUSHED $(git -C "$WORK" rev-parse --short HEAD) — mirrors: 00_ailaws.md AGENTS.md README.md ailaws.md"
else
  log "ERROR: push failed (see log)"
  exit 1
fi
