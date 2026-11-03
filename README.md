# AI LAWS

### Universal AI Laws & Direct Autonomous Execution Rules

The canonical home of the **AI Laws** — the standing rules that govern how AI agents working for the owner operate: how they execute directives, keep records, handle evidence, and hold themselves accountable for errors.

> **Governed repository.** This is not a casual document repo. The AI Laws change only by the owner's order, every change is made here first, and every change is archived, backed up, reversible, and logged with strict timestamps. Nothing is deleted and nothing is hidden.

---

## The Laws

The full text of the laws lives in the law file:

- **[00_ailaws.md](https://github.com/Tonypost949/ailaws/blob/main/00_ailaws.md)** — the canonical full text of the Universal AI Laws & Direct Autonomous Execution Rules.

The laws cover, among other things: direct execution of the owner's directives, the task system and zero loss of information, autonomous execution authority, zero human homework (the AI does the work itself), explicit full URLs and file paths, official-records and primary-evidence primacy, and the Error Coin accountability ledger.

## Rules — the testing ground for future laws

New provisions do not start as laws. They enter as **rules**, are tested on live work with the evidence recorded, and become laws only when the reasons are proven and the owner orders the merge — nothing lost along the way.

- **[RULES.md](https://github.com/Tonypost949/ailaws/blob/main/RULES.md)** — the rules system: the pipeline (proposed → testing → proven → law, only on the owner's order), and the difference between a law, a rule, a tool, and an idea/task.
- **[rules/RULES_REGISTER.md](https://github.com/Tonypost949/ailaws/blob/main/rules/RULES_REGISTER.md)** — every rule and its status. Currently under test: the owner's **AILAWS V2 (aitechverse)** draft, listed 2026-11-03 as rules RULE-2026-V2-01 … V2-09 — **listed for testing, not adopted as law**.
- **[rules/RULE_TEST_LOG.md](https://github.com/Tonypost949/ailaws/blob/main/rules/RULE_TEST_LOG.md)** — dated records of rules applied on live work; a promotion verdict may only cite what is recorded there.

## Governance

How this repository is run is itself part of the record:

- **[AILAW_CHANGE_GOVERNANCE.md](https://github.com/Tonypost949/ailaws/blob/main/AILAW_CHANGE_GOVERNANCE.md)** — the change rules: GitHub-first, local copies are pulled from GitHub, only the owner changes the laws, and any unauthorized change — if one ever happens — is recorded in full, hidden from no one, and reverted by a logged commit.
- **[AILAW_ACTIVITY_LOG.md](https://github.com/Tonypost949/ailaws/blob/main/AILAW_ACTIVITY_LOG.md)** — strict timestamp notes on all AILAW-related activity: orders, approvals, revisions, archives, backups, and pulls.
- **[archive/](https://github.com/Tonypost949/ailaws/tree/main/archive)** — pre-change state records, so every change can be traced back and undone.

The AI Laws are, inherently, record-keeping tools: the history of this repository — every commit, every log entry, every archived state — is part of how they work.

## Repository layout

| Path | What it is |
|---|---|
| `00_ailaws.md` | Canonical full text of the AI Laws |
| `RULES.md` | The rules system — how new provisions are tested before they can become laws |
| `rules/` | Rules register, test log, and verbatim candidate texts under test |
| `AILAW_CHANGE_GOVERNANCE.md` | The rules for changing the laws |
| `AILAW_ACTIVITY_LOG.md` | Timestamped log of all AILAW-related activity |
| `archive/` | Pre-change state records (undo points) |
| `docs/` | Supporting documentation |
| `.agents/` | Agent tooling and skills maintained alongside the laws |

## Change process

1. The owner orders a change (or approves one).
2. The pre-change state is recorded in `archive/` with a timestamp.
3. The change is committed here, on GitHub, first — with a commit message that says what changed and under whose order.
4. The activity is entered in `AILAW_ACTIVITY_LOG.md` with a full timestamp.
5. Local copies everywhere else are then refreshed **from** GitHub.

Undoing a change is done the same way as making one: a new commit that reverts it, logged in the open. History is never rewritten.

## History

Full commit history: https://github.com/Tonypost949/ailaws/commits/main

---

*Maintained under the owner's standing directives. The laws themselves are the authority for how the agents that run on them behave; this page is only the front door.*
