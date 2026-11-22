# review

Skills for judging a change someone else wrote, or one you wrote before you ask a human to look.
The development pipeline's closing stages ([refactor-review](../development/refactor-review/SKILL.md),
[devils-advocate](../development/devils-advocate/SKILL.md),
[tyr-verdict](../development/tyr-verdict/SKILL.md)) review work *you are building* inside the
pipeline. This family reviews *a change as it arrives*: a pull request, a branch, a diff.

```
            before                 during                                        after
  pr-prep ─────────► code-xray ─► peer-review ◄── test-review         ──► re-review ──► review-retro
  author mode:       history:      claim · risk map · lenses A–P          (peer-review)    record · metrics
  self-review,       hotspots,     verify · gap sweep · comments      ◄── concurrency-review   · proposals
  split, describe    coupling,     coverage · recommendation          ◄── appsec (PR tier)
  readiness mode:    knowledge
  is it reviewable?
```

| Skill | What it does |
|---|---|
| [pr-prep](pr-prep/SKILL.md) | The author's side. Author mode self-reviews with the omission checklist, checks size and shape, proposes a split, and writes the description (claim, acceptance criteria, how to verify, risk, reading order) without priming the reviewer. Readiness mode checks someone's PR before review: the claim, alignment (Exact / Missing / Tangling), process gaps, and Ready / Ready with gaps / Not ready. |
| [code-xray](code-xray/SKILL.md) | Behavioural code analysis from `git log`, with a read-only stdlib script: hotspots, function-level X-rays, complexity growth, change coupling and the missing co-change, clone twins, code age, knowledge maps. PR mode feeds peer-review's risk map; codebase mode ranks refactoring targets. Knowledge data routes reviews; it never rates people. |
| [peer-review](peer-review/SKILL.md) | The gate. Claude Code's built-in `/code-review` recipe (independent finder angles, a CONFIRMED/PLAUSIBLE/REFUTED verify pass, a gap sweep, capped ranked findings) plus what the literature says reviewers miss: the claim, omissions, risk-ranked attention in units under 400 lines, sixteen lenses, comments with evidence and a fix, a coverage statement, a recommendation a human makes, and a re-review of the fixes. |
| [test-review](test-review/SKILL.md) | The specialist for lens K. Would each test fail if the behaviour broke? Traceability from every claim to its tests, a named mutation per changed branch, edges, determinism, doubles, clarity; a mutation probe confirms a test that can't fail. |
| [concurrency-review](concurrency-review/SKILL.md) | The specialist for lens G. Shared state, check-then-act, atomicity, deadlock, async, pools, transactions, idempotency and delivery, distributed locks. Every scenario is an interleaving; CONFIRMED needs a reproduction. |
| [review-retro](review-retro/SKILL.md) | After review. A retrievable record of one PR, and over many reviews: metrics by type, severity, lens and area (never by person), and checklist, rule and lint proposals for a human to approve. |

## Running all of them on one PR

[`harness/prreview.py`](../../harness/README.md#one-pull-request-through-every-review-skill--prreviewpy) runs
the whole family on a single pull request: pr-prep's readiness pass, code-xray's script, peer-review's lens
groups with test-review, concurrency-review and appsec routed in by what the diff touches, one verifier per
candidate, the gap sweep, synthesis, and a report whose recommendation is computed by peer-review's rule.
`--re-review` verifies the fixes, `--retro` writes the record, and `--post` leaves one COMMENT review. Every
skill above still works on its own, in any agent, without it.

```bash
python3 harness/prreview.py --repo . --pr 482
```

## Install

```bash
npx skills add izentenosmith/skills --skill pr-prep code-xray peer-review test-review concurrency-review review-retro
```

The repo is public, so no GitHub account is needed; the flags (`-a`, `-g`, `-y`) are in the [root README](../../README.md#install-with-npx). Or copy the
folders. Each is self-contained: `SKILL.md` plus its reference docs (and code-xray's script), no symlinks.

Invoke by name, or let the description trigger it:

```
/pr-prep                          prepare my branch for review and write the description
/pr-prep readiness 482            is PR #482 ready to review?
/code-xray                        where is the technical debt that costs us most?
/peer-review 482                  review PR #482
/peer-review deep 482 --comment   Deep tier, then post the comments (asks first)
/test-review 482                  would these tests catch a regression?
/concurrency-review               review the worker pool change for races
/peer-review re-review 482        verify the fixes against the last review
/review-retro 482                 write the record of the merged PR
/review-retro last quarter        metrics and checklist proposals across reviews
```

## How peer-review relates to the built-in `/code-review`

| | built-in `/code-review` | peer-review |
|---|---|---|
| Finder angles | 8–10: line scan, removed behaviour, cross-file, language pitfalls, wrappers, reuse, simplification, efficiency, altitude, conventions | the same, plus failure paths, concurrency, data contracts, **intent alignment**, **omissions**, **tests**, **security**, readability — with test-review, concurrency-review and appsec as specialists |
| Verify | one verifier per candidate, three verdicts | the same rubric; plus a re-run rule for flaky evidence |
| Context | the diff and CLAUDE.md | the diff, **the claim** (PR body, issue, commits, brief — via pr-prep), the rules, CI, **git history** (via code-xray) |
| Attention | uniform | **risk map**: Deep triggers, hotspots, change coupling, knowledge; review units ≤ 400 lines |
| Output | ranked findings with a failure scenario | the same, plus severity labels, alignment, questions, what's good, **coverage**, **recommendation** |
| After | `--fix`, `--comment` | the same (posting confirms first), plus a **re-review** verification round and **review-retro** |

Use the built-in for a fast bug-only pass. Use peer-review when the review is the gate.

## Do they work?

One eval per skill (evals 49–54), each run three times against no skill, standalone (only the skill's own folder, as a single-skill install). Delta, out of 1.00: peer-review **1.00** vs 0.29, pr-prep **0.97** vs 0.31, code-xray **1.00** vs 0.40, test-review **1.00** vs 0.20, concurrency-review **1.00** vs 0.39, review-retro **1.00** vs 0.36 (re-run 2026-11-05 after it was made to stand alone, against a fresh baseline). The fixtures, the planted traps and the controls are in [evals/README.md](../../evals/README.md#the-review-family-evals-4954).

## The theory underneath

Every finding cites a principle: R1–R32 ([peer-review](peer-review/theory.md)), PP ([pr-prep](pr-prep/theory.md)),
X ([code-xray](code-xray/theory.md)), TR ([test-review](test-review/theory.md)),
CR ([concurrency-review](concurrency-review/theory.md)) or RR ([review-retro](review-retro/theory.md)), or a
heuristic ID.

| Source | What it contributes |
|---|---|
| Cohen et al., *Best Kept Secrets of Peer Code Review* (the Cisco study) | Review units of 200–400 lines, rate and session limits, author preparation and its priming risk, checklists against omissions, verification of fixes, metrics that must never rate people |
| Tornhill, *Software Design X-Rays* | Hotspots, change coupling, "catch the absence of change", clone twins, complexity growth on a branch, code age, knowledge maps for reviewer suggestion and knowledge loss |
| OWASP, *Code Review Guide* v2 | Source-to-sink tracing, the attack-surface diff checklist, the code-crawling grep lists, and when a diff review must escalate to a full security review |
| Martin, *Clean Code* | Chapter 17's heuristics (C/E/F/G/J/N/T), the concurrency chapters and their checklist, F.I.R.S.T. and clean tests, and where the advice is contested |
| Liddament, *Effective Code Review* | Evolvability defects as most of review's value, the reviewer's question list, good comments, small focused commits |
| Kamalı et al., *Rethinking Code Review in the Age of AI* (2026) | PR-issue alignment classes, change impact analysis, risk lanes, claim + evidence + confidence, human gates, prompt injection via PR content, review knowledge as organisational memory |
| Claude Code's built-in `/code-review` recipe | The engine: finder angles, the three-verdict verify pass, the gap sweep, caps, the findings-tool contract |
