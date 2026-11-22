---
name: skill-word-cuts-2026-11-21
description: Cutting the development SKILL.md files toward ~2,000 words; three cuts kept, five reverted, and which passages proved load-bearing
type: decision
source: evals/README.md (word cuts, iteration 58), commits 7db4bed..367a1c9, session 2026-11-21
verified: 2026-11-21
volatility: high
---

Each development SKILL.md was cut toward about 2,000 words (detail moved into new reference files),
and evals 0–5, 27, 58 and 60–75 were run three times on the cut text as iteration 58, reusing the
iteration 55/57 baselines (`run.py --baseline-ref none`; the baseline ref had not moved). The rule
was to keep a skill's cut only if none of its three evals dropped on delta or capability.

Kept: acceptance-tests (2,431 words), tyr-verdict (2,495), nexus (2,510). Reverted whole, at skill
level: agent-brief, refactor-review, tdd, devils-advocate, architect-deep-dive. No skill reached
2,000; what remains is templates, graded tokens and headings `harness/` points at.

**Load-bearing text the cuts found** (keep it in any later attempt):
- agent-brief: the prior-art examples. Without them, and with "never file paths" beside them, runs
  pointed at "the parametrized test" instead of naming the suite (eval 1).
- refactor-review: the explanation behind noted smells and their **Promote if** line; all three
  eval 66 runs dropped the condition.
- architect-deep-dive: the question-format rules; one eval 74 question lost sections, and Haiku
  already loses this format at full length.

tdd (one red test in eval 62) and devils-advocate (one missing vacuity argument in eval 4) may
have been noise at n=3. A second attempt should restore only the passages above and re-run those
skills' evals, rather than revert whole skills. Two moved sections are not exercised by any of the
24 evals: tyr-verdict's GO/ESCALATED handoff (`handoff.md`, reached only by eval 15) and the
reverted skills' runs, kept in the workspace under `iteration-58/reverted-cuts/`.
