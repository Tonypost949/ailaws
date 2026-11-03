# RULES — The Testing Ground for the AI Laws

## What this system is

Ordered by the owner, 2026-11-03 15:34 PST (verbatim order and clarification preserved in AILAW_ACTIVITY_LOG.md):

- The owner may update the AI Laws directly — that remains his right at any time.
- The **better route, and the standing one**, is: a new provision enters first as a **RULE**, is tested on live work over time, and only becomes a **LAW** when the reasons for it are proven — with the exact evidence recorded — and the owner orders the merge.
- Nothing is lost along the way: a rule's text, its reasons, its test record, and its verdict all stay in this system permanently, whether it is promoted, kept as a rule, turned into a tool, or retired.

**Rules are not laws.** A rule listed here has no law status, governs nothing by itself beyond the live-work test the owner ordered, and is never presented as a law. Promotion is the only way a rule becomes a law, and promotion happens only under the AILAW_CHANGE_GOVERNANCE.md process, on the owner's direct order.

## Four different things — never mixed

| Kind | What it is | Where it lives |
|---|---|---|
| **LAW** | Proven, governing, the owner's text verbatim | 00_ailaws.md (canonical) |
| **RULE** | A provision under test, or a standing working rule not (yet) a law | This system: RULES.md + rules/ |
| **TOOL** | A repeated action formalized into an executable / skill — wanted and useful, but a procedure, not a norm | .agents/ skills + the task system |
| **IDEA / TASK** | Wanted but not needed as a norm; one-off or exploratory work | The task system |

A repetitive *wanted* action is a tool or a task. A rule is a candidate *norm*: it claims the work should always (or never) be done a certain way. That claim is what has to be proven before it can be a law.

## The pipeline

1. **PROPOSED** — Entered in rules/RULES_REGISTER.md with: the exact text, who proposed it and when, the reason it is believed needed, and the problem it answers. Entry in the register is a GitHub-first commit, logged in AILAW_ACTIVITY_LOG.md.
2. **TESTING** — Applied on live work. Every application is recorded in rules/RULE_TEST_LOG.md with timestamp, the work it touched, what happened, and whether the rule helped, did nothing, or caused friction — including any collision with platform requirements (approval cards, safety limits), which are facts of the test, not verdicts by themselves.
3. **PROVEN or NOT PROVEN** — When the test record is enough, the register entry is marked:
   - **PROVEN** — the exact reasons are stated from the test record (dated cases, not opinion), and the rule is ready to be offered for promotion.
   - **NOT PROVEN / STAYS A RULE** — useful as a working rule or convention, but the case for law is not made. It stays a rule. That is a normal outcome, not a failure.
   - **BECOMES A TOOL** — the provision turned out to be a procedure: it is formalized as a tool/skill and the register entry points to it.
   - **RETIRED** — no longer used. The entry and its whole record stay; nothing is deleted.
4. **PROMOTED TO LAW** — Only on the owner's direct order, and only through AILAW_CHANGE_GOVERNANCE.md: GitHub-first revision of the law text, prior version archived, change undoable, activity logged with strict timestamps. The register entry is then marked PROMOTED with the law's number and the commit that merged it, and its full history stays in the register.

Direct law changes by the owner (skipping the pipeline) remain possible at any time, exactly as he ordered — they are logged the same way, and this system is then updated from the law, never the other way around.

## Rule entry format

Every register entry carries the same fields, so a promotion decision never has to guess:

- **ID** (RULE-YYYY-NNN)
- **Title**
- **Status** — PROPOSED / TESTING / PROVEN / NOT PROVEN–STAYS A RULE / BECAME A TOOL / RETIRED / PROMOTED (with law number + commit)
- **Text** — exact wording, or the file that holds it verbatim
- **Source** — who wrote/proposed it, where, when (link or path)
- **Reason claimed** — why it is believed needed, in the proposer's terms
- **Test record** — pointer to rules/RULE_TEST_LOG.md entries
- **Collisions / limits noted** — any platform or system requirement the rule cannot override
- **Verdict + exact reasons proven** — filled only when the record supports it

## Access

This system lives **under the AI Laws environment**: this repository (https://github.com/Tonypost949/ailaws). Start here (RULES.md), the register is rules/RULES_REGISTER.md, the test log is rules/RULE_TEST_LOG.md, and candidate texts sit in rules/candidates/. Local copies are pulled from GitHub, per governance.
