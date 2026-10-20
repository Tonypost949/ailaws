# OSINTNeoAI Universal AI Laws & Autonomous Agent Package

One-click bootstrapper to enforce autonomous execution rules, isolated user data schemas, and shared tooling across all AI models (Gemini, Claude, GPT, Antigravity, local LLMs).

**Canonical source of truth:** `C:\Amd949609_Antigravity_v1\00_ailaws.md`
**Law repo (mirror):** `https://github.com/Tonypost949/ailaws`
**Working code checkout (NOT a source of truth):** `https://github.com/Tonypost949/OsintNeoAi.git`

### 🚀 Quick Install (PowerShell)
```powershell
irm https://raw.githubusercontent.com/Tonypost949/ailaws/main/setup_universal_ai.ps1 | iex
```
Or double-click `install_ai_ecosystem.cmd` (same folder as this file).

### ⚡ Universal Prompt (Works with any AI)
```text
read C:\Amd949609_Antigravity_v1\00_ailaws.md and execute
```

### 📄 Files in this repo
| File | Purpose |
| --- | --- |
| `00_ailaws.md` | Canonical Universal AI Laws (16 laws + OVERRIDE OPTIONS incl. SOURCE OF TRUTH RULE) |
| `AGENTS.md` | Identical mirror, auto-loaded by agents that read `AGENTS.md` |
| `README.md` | Identical mirror so the laws are the first thing seen on the repo page |
| `ailaws.md` | Identical mirror for the legacy `C:\ailaws.md` prompt path |
| `setup_universal_ai.ps1` | Idempotent installer: lays down laws + user folder skeleton |
| `install_ai_ecosystem.cmd` | Windows one-click wrapper for the installer |

All four law mirrors are generated from the canonical file by
`C:\Amd949609_Antigravity_v1\tools\ailaws_github_sync.sh`, which refuses to push if
`SOURCE OF TRUTH RULE` or Law 16 is missing from the canonical file.
