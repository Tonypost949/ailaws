#!/usr/bin/env bash
# trinity_intake.sh — run evidence records through The Trinity before they are
# accepted into the Evidence Locker.
#
# Law: THE TRINITY: FOUNDATIONAL ENGINE FOR TRUTH & ACCURACY
#       C:\Amd949609_Antigravity_v1\00_ailaws.md
#
# Usage:
#   trinity_intake.sh <records.jsonl> [more.jsonl ...]
#   trinity_intake.sh --selftest
#
# Input : JSONL, one evidence record per line
#           {"id","claim","source":{"tier"},"observed_at","collected_at",
#            "location":{"lat","lon"},"previous_location":{"lat","lon","at"},
#            "value","baseline":{"n","mean","stdev"},"corroborations":[{"tier","independent"}],
#            "requires_mechanism","mechanism","sha256","payload_sha256"}
# Output: C:\Amd949609_Antigravity_v1\EVIDENCE_LOCKER_MASTER\trinity\<stamp>\
#           verdicts.jsonl   — one verdict per record (accuracy axis)
#           audit.jsonl      — immutable lineage (transparency axis)
#           summary.md       — human-readable gate report
# Nothing is deleted or moved; records already in the locker are never altered.
set -uo pipefail

TOOLS="/mnt/c/Amd949609_Antigravity_v1/tools"
GATE="$TOOLS/trinity_gate.py"
OUTROOT="/mnt/c/Amd949609_Antigravity_v1/EVIDENCE_LOCKER_MASTER/trinity"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
PY=$(command -v python3 || echo /usr/bin/python3)

if [ "${1:-}" = "--selftest" ]; then exec "$PY" "$GATE" --selftest; fi
[ $# -lt 1 ] && { echo "usage: $0 <records.jsonl> [more.jsonl ...] | --selftest"; exit 2; }

OUTDIR="$OUTROOT/$STAMP"
mkdir -p "$OUTDIR"
: >"$OUTDIR/verdicts.jsonl"
: >"$OUTDIR/audit.jsonl"

printf '%s\n' "# Trinity intake — $STAMP" "" >"$OUTDIR/summary.md"

rc=0
for f in "$@"; do
  [ -f "$f" ] || { echo "missing input: $f" >>"$OUTDIR/summary.md"; rc=1; continue; }
  before=$(wc -l <"$OUTDIR/verdicts.jsonl")
  "$PY" "$GATE" --input "$f" --out "$OUTDIR/.part.jsonl" --audit-log "$OUTDIR/audit.jsonl" >"$OUTDIR/.part.json"
  cat "$OUTDIR/.part.jsonl" >>"$OUTDIR/verdicts.jsonl"
  {
    printf '## %s\n\n' "$(basename "$f")"
    printf '```json\n'; cat "$OUTDIR/.part.json"; printf '```\n\n'
  } >>"$OUTDIR/summary.md"
  rm -f "$OUTDIR/.part.jsonl" "$OUTDIR/.part.json"
  added=$(( $(wc -l <"$OUTDIR/verdicts.jsonl") - before ))
  echo "processed $f -> $added verdict(s)"
done

{
  printf '\n## Verdict table\n\n| record | verdict | gates failed |\n|---|---|---|\n'
  "$PY" - "$OUTDIR/verdicts.jsonl" <<'PYEOF'
import json, sys
for line in open(sys.argv[1]):
    v = json.loads(line)
    g = v["accuracy"]
    print(f"| {v['record_id']} | {v['verdict']} | {', '.join(g.get('gates_failed') or ['-'])} |")
PYEOF
} >>"$OUTDIR/summary.md"

echo "outputs: $OUTDIR"
ls -1 "$OUTDIR"
exit "$rc"
