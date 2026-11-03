# AILAW CHANGE GOVERNANCE — GitHub-First Rule

## The directive (user's exact words, 2026-11-03 14:58 PST)

> OK SO FROM NOW ON, CHANGES TO AI LAWS IS DONE THROUGH GITHUB FURST, THEN THE COPIES LOCALLY BLA BLA COME FROM GH ,  IF I TELL YOU TO CHANGE AN AILAW IN ANY WAY, OR ANOTHER SYSTEM DOES AND THE CHANGES ARE APROVED REVISE, ARCHIVE, BACKUP, MAKE IT TO BE UNDOABLE ETC AND KEEP STRICT TIMESTAMPS NOTES ETC ON ALL AILAW REALTED ACTIVITY

## What this means, in force from 2026-11-03 14:58 PST

1. **GitHub first.** Every change to the AI Laws is made in this repository (https://github.com/Tonypost949/ailaws) before it exists anywhere else. This repo is the change source for the laws.
2. **Local copies come from GitHub.** After a change lands here, local copies (PC, VM, any other system) are pulled/refreshed FROM GitHub. No local-first edits to the laws.
3. **Approval gate.** A change is made only when it is approved: ordered by the user, or proposed by another system/AI and approved. Unapproved changes do not land.
4. **Every approved change is processed the same way:** revise the law text, archive the prior version, back it up, and keep the change **undoable** (git history is never rewritten; a change is undone by a new revert commit, never by deleting history).
5. **Strict timestamp notes.** Every AILAW-related activity — an order, a proposal, an approval, a revision, an archive, a backup, a pull of a local copy — is entered in AILAW_ACTIVITY_LOG.md with a full timestamp (date, time, timezone) and what exactly was done, by whom, under whose approval.
6. **Nothing is deleted.** Superseded law text stays in git history and in archive copies, per the standing never-delete rule.

## Pre-change state when this rule took effect (recorded 2026-11-03 14:59 PST)

- HEAD commit: d1215c9a92f3313a54ba461c60fd2a5b669a6613 ("Add notebooklm-extract skill and real Error Coin / gap-naming examples (2026-11-03)")
- Law file blob: 76a2f9f0a9cd62d4af850dcb69743bce83a492bd (18,987 bytes), present identically at 00_ailaws.md, AGENTS.md, README.md, ailaws.md
- Undo for this governance commit: revert it by a new commit; the pre-change state above remains reachable in history.
