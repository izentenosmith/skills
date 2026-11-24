# A cut-only gardener script for skill folders

**The idea.** A harness script, after peterpme/skill-gardener, that asks Claude to propose cuts to a
skill folder (duplicated rules, narration, stale dates, lines nothing backs, prose CI already
enforces) and applies them through a deterministic verifier: removals only, no number, path or
command changed, no guard-rail line touched, at most 15% of a file's words per run, kept only if the
skill's evals hold.

**Why it's out.** Built on 2026-11-24 and dropped before it merged or ran: the owner found it less
effective than pruning a skill through Anthropic's skill-creator, against the skill-authoring best
practices, with the skill's evals as the check. A mechanical verifier refuses most whole-paragraph
cuts (headings, guard-rail words), so it promised a small saving for a second toolchain to maintain.
The word cuts of 2026-11-21 (`.memory/notes/skill-word-cuts-2026-11-21.md`) already showed that a
cut is decided by the evals, not by the kind of text removed.

**Evidence.** Never committed to `main`; the decision is recorded with the change that would have
added it (the 2026-11-24 improvements branch).

**What would reopen it.** Skill-creator pruning repeatedly leaving the same kind of dead text
(a removed path, a duplicated rule) that a deterministic check would have caught.
