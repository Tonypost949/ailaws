# AI Laws — single source of truth

**One writable law file. Everything else is generated.** This repo exists so the laws can never be silently
eroded by a divergent fork again (that is exactly what happened between 2026-09-18 and 2026-10-20: the
`SOURCE OF TRUTH RULE` had been stripped from `AGENTS.md` and `ailaws.md`).

## Canonical file (the only one you may edit)

```
C:\Amd949609_Antigravity_v1\00_ailaws.md
```

That file lives in the user folder, per the SOURCE OF TRUTH RULE.
`C:\OsintNeoAi` is a working code checkout and is **never** a source of truth.

## Generated mirrors (never hand-edit — they are overwritten every 2 hours)

| Path | How it is produced |
| --- | --- |
| `C:\Amd949609_Antigravity_v1\AGENTS.md` | copy of canonical |
| `C:\OsintNeoAi\00_ailaws.md`, `AGENTS.md`, `.agents\AGENTS.md` | copies of canonical (kills checkout forks) |
| `/home/osintneoai/00_ailaws.md`, `AGENTS.md`, `.agents/AGENTS.md` | **symlinks** to the canonical file |
| `00_ailaws.md`, `AGENTS.md`, `README.md`, `ailaws.md` in this repo | copies of canonical |

Because the three WSL agent paths are symlinks, the agent harness reads the master directly — there is
physically only one law file to edit.

## Tools

### `tools/ailaws_github_sync.sh`
Regenerates every mirror from the canonical file, commits and pushes to `main`, and **refuses to push**
(exit 2) if the canonical file is missing any of these clauses:

`SOURCE OF TRUTH RULE` · `OVERRIDE OPTIONS` · `ABSOLUTE PROHIBITION ON PERMISSION-SEEKING` · `ERROR COIN` · `YOLO Mode` · `OFFICIAL RECORDS, PRIMARY EVIDENCE`

Schedule: WSL crontab `17 */2 * * *`, started at boot by `/etc/wsl.conf` → `[boot] command = service cron start`.
Log: `C:\Amd949609_Antigravity_v1\tools\logs\ailaws_github_sync.log`

### `tools/ailaws_verify.sh`
Audits every copy on the machine plus all four raw GitHub URLs, byte-for-byte, and lists any missing clause.
Exit 0 = healthy. Schedule: WSL crontab `42 3 * * *`.
Log: `C:\Amd949609_Antigravity_v1\tools\logs\ailaws_verify.log`

### `setup_universal_ai.ps1`
Idempotent installer for a fresh machine: writes the laws, creates the user-folder skeleton, backs up anything it
overwrites, and aborts before writing if the source laws file is missing the SOURCE OF TRUTH RULE.

## Known blocked paths (Windows UAC)

`C:\ailaws.md` (stale 5,589-byte pre-2016-09 fork) and `C:\AGENTS.md` (absent) sit in the C:\ root, which is
owned by `BUILTIN\Administrators`; WSL has no non-interactive elevation path, so they cannot be rewritten from
here. No documented entry point references them — every prompt, installer and README now points at
`C:\Amd949609_Antigravity_v1\00_ailaws.md`. Fix, from any already-elevated shell:

```
copy /Y "C:\Amd949609_Antigravity_v1\00_ailaws.md" "C:\ailaws.md"
copy /Y "C:\Amd949609_Antigravity_v1\00_ailaws.md" "C:\AGENTS.md"
```

## The Trinity — truth & accuracy engine

`THE TRINITY: FOUNDATIONAL ENGINE FOR TRUTH & ACCURACY` is law, and it now has teeth:

| Tool | Purpose |
| --- | --- |
| `tools/trinity_gate.py` | Three-gate engine. Gate 1 physics/reality (coordinate ranges, impossible travel, temporal order, required mechanism, hash provenance) → Gate 2 Bayesian posterior from source tier + independent corroboration → Gate 3 z-score outlier vs longitudinal baseline. |
| `tools/trinity_intake.sh` | Wrapper: runs a JSONL of evidence records, writes `verdicts.jsonl` + immutable `audit.jsonl` + `summary.md` under `C:\Amd949609_Antigravity_v1\EVIDENCE_LOCKER_MASTER\trinity\<stamp>\`. |
| `tools/test_trinity_gate.py` | 35 unit tests incl. the law's own precedents (Wegener 1912 → passes only when seafloor-spreading physics is supplied; Semmelweis 1847 → escalated as an outlier, not accepted). |

**Accuracy and transparency are separate outputs.** Every verdict carries the gate outcome *and* an audit record:
`rule_version`, `record_sha256`, full record snapshot, baseline snapshot, gate sequence, per-gate numbers.

**Verdicts:** `ACCEPT`, `FLAG_CORROBORATE` (gate 2 below threshold), `ESCALATE_HIGH_SCRUTINY` (gate 3 outlier),
`QUARANTINE` (gate 1 violation). A record can trip several gates; every required action is reported and the primary
verdict is the most severe (`QUARANTINE > ESCALATE > FLAG_CORROBORATE > ACCEPT`).

**Nothing is destroyed.** `recheck()` re-runs a stored record against new corroboration or a new baseline, so a record
that failed a gate today can pass later — exactly the Continental Drift / Semmelweis precedent behaviour.

```bash
python3 tools/trinity_gate.py --selftest
python3 -m unittest test_trinity_gate -v      # from tools/
bash tools/trinity_intake.sh records.jsonl
```

See `tools/examples/trinity_demo_run/` for a real run: official deed `ACCEPT` (posterior 0.95), anonymous tip
`FLAG_CORROBORATE` (0.30), impossible 5-minute Huntington Beach → San Diego drive `QUARANTINE` (implied 4,400 km/h),
unexplained 4-ft property-line move with no recorded instrument `QUARANTINE` (no physical mechanism), and a 2.45M
comparable against an 812k ± 95k baseline `ESCALATE_HIGH_SCRUTINY` (z = 17.2) with both gate 2 and gate 3 actions listed.
