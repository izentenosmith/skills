# Report — Severity, Verdicts, the Recommendation, Templates

> How a peer review is graded and written down. A diff review gets **findings and a
> recommendation, not a 0–10 score**. A score belongs to a codebase audit, which is what
> `appsec` and the other audit skills produce. Every finding names
> its principle from [theory.md](theory.md) (R-n) or a heuristic ID from
> [heuristics.md](heuristics.md). A finding with neither is taste.

---

## Severity

Severity reads **reachability** (who can trigger it), **blast radius** (how much breaks or
leaks), and **reversibility** (whether the damage can be undone). Say which you graded against
when it isn't obvious.

| Severity | Meaning | Anchors |
|---|---|---|
| **blocker** | Merging this causes a real failure: wrong results, data loss or corruption, a security hole, an outage, or a break for existing callers | Injection or missing authorisation on a reachable path; a committed secret; a migration that locks or drops production data; a crash or wrong result on a realistic input; a race that loses writes; a breaking API or wire change with live consumers; the change doesn't do the core thing it claims (alignment Missing on the main requirement) |
| **major** | A significant defect or cost that should be fixed before merge, or deferred deliberately with a tracked issue | A wrong result on a rare-but-reachable path; an unhandled error path that leaves state inconsistent; new behaviour with no test, or a test that can't fail; a missing co-change with strong history (≥ 80%); a clear quoted rule violation; new complexity in a hotspot; a secret or personal data in logs; tangling that hides a behaviour change |
| **minor** | A real evolvability or clarity defect with a stated cost | A misleading name; a comment the diff made wrong; duplication of an existing helper; a flag argument; a magic value; a reader-confusing construct (R12); a missing doc update |
| **nit** | Polish. Optional. Grouped into one line | Wording, small simplifications, ordering |

**Blocker or major, when a claim is only partly done.** A claimed behaviour that isn't implemented
is a **blocker** when it is part of what the change says it does. That holds even if it isn't the
headline, because the change ships a promise it doesn't keep. It is **major** when the claim is
incidental, such as a docs mention or a nice-to-have the description hedges. A wrong result on
every input in a realistic configuration is a blocker, whatever the claim says.

**Moving severity.**

- Raise one step for code that is a hotspot, a public interface, or reached by anonymous users.
- Lower one step for admin-only or internal-only reachability, or behind a default-off flag, and say
  which.
- A security weakness blocked today by another control stays a finding, one step lower, with the
  control named (OCR p.15–16).
- **Never lower a blocker because the fix is inconvenient.**

**Type**, one per finding: `bug` · `security` · `test` · `evolvability` · `process` (size,
tangling, missing description, missing tooling) · `conventions`.

## Verdicts (Phase 3)

| Verdict | Needs | Kept? |
|---|---|---|
| **CONFIRMED** | The inputs or state that trigger it, the wrong result, and the quoted line | Yes |
| **PLAUSIBLE** | A real mechanism with an uncertain trigger (timing, environment, configuration), and what would confirm it | Yes. Deep keeps all of them. Standard keeps the ones a maintainer would act on |
| **REFUTED** | Factually wrong (quote the line), provably impossible (show the type, constant or invariant), handled elsewhere (cite the guard), or pure taste | No |

Evolvability, process and convention findings are verified against their **cost**. The cost is
CONFIRMED when you can point at it: the duplicated helper, the quoted rule, the second switch, the
history count. It is REFUTED when the "cost" is only a preference.

## The recommendation

Exactly one. It follows from the findings. It is never a mood.

| Recommendation | When |
|---|---|
| **Approve** | No blocker, no major. The claim is aligned (Exact). Coverage is complete for the tier |
| **Approve with nits** | No blocker, no major. Minors and nits only, and each is the author's call |
| **Request changes** | Any blocker, or any major not deferred with a tracked issue |
| **Needs discussion** | Unanswered questions decide whether something is a defect; or alignment is Missing or Tangling and the scope needs a decision; or the change should be split before it can be reviewed with confidence; or an escalation (appsec, a design question) must happen first |

**The recommendation is advice.** A person approves and merges (R32). When coverage was partial, such
as a skipped unit, a lens that didn't run, or a change too large for confident review, the
recommendation can't be **Approve**. Use **Needs discussion** and say what wasn't covered.

## Caps

| Tier | Findings above `nit` | Nits |
|---|---|---|
| Quick | 5 | one grouped line |
| Standard | 10 | one grouped line |
| Deep | 20 | one grouped line |

**Questions and the claim section don't count toward the cap.** Neither does a contradiction
between the claim and the code. It goes under Claim. Don't move a finding into Questions to make
room for another. A question is only for intent you genuinely can't recover.

When more survive than the cap allows, keep the most severe. Correctness and security outrank
evolvability at equal severity. Say how many were cut and of what type ("6 further minor
evolvability findings not listed"). Never cut a blocker. If the user asked for every finding,
there's no cap.

## Findings-tool mapping

When the host offers a findings-report tool (for example `ReportFindings`), each finding maps as:

| Tool field | From |
|---|---|
| `file`, `line` | the anchor |
| `summary` | the one-line claim |
| `short_summary` | the claim compressed to ≤ 60 characters |
| `failure_scenario` | the scenario (bugs), or the concrete cost (other types) |
| `category` | the lens slug: `correctness`, `removed-behavior`, `impact`, `language-pitfall`, `wrapper`, `failure-path`, `concurrency`, `data-contract`, `intent`, `omission`, `test-coverage`, `security`, `readability`, `altitude`, `reuse`, `simplification`, `efficiency`, `conventions` |
| `verdict` | CONFIRMED or PLAUSIBLE |

Call the tool once, ranked most severe first. Then print the rest of the report as text, without
repeating the findings. After fixes land, call it again with an `outcome` on each finding.

---

## The report template

```markdown
# Review — <PR title or branch> @ <short sha>

**Tier:** <Quick | Standard | Deep> — <why>. **Scope:** <n> files, <m> meaningful lines changed
(<excluded: lockfiles, generated…>), <k> review units.

## Claim
<One or two sentences: what the change claims to do and what done looks like, with the source:
PR body / issue #n / commits / derived from code.>
**Alignment:** <Exact | Missing: <what> | Tangling: <which hunks> | Missing + Tangling>
<Any contradiction between the claim and the code, stated plainly.>

## Risk map
| Unit | Files | Risk | Why |
|---|---|---|---|
| U1 | `billing/invoice.py`, `tests/test_invoice.py` | high | money; hotspot #3; complexity +14% |
| U2 | … | low | … |
<History signals, one line per file that has any — see history-signals.md — with a data-quality
line first: window, commits, exclusions.>

## Findings
<Ranked. For each:>
### PR-1 · blocker · bug · `src/pricing.ts:42`
<the comment, in the comments.md shape: claim, why, evidence, suggestion>
*Lens A · CONFIRMED · R24*

<…>

**Nits:** <one line, grouped>. <n> further findings cut by the cap: <types>.

## Questions for the author
1. <question — and what the answer changes>

## What's good
- <specific, earned, worth repeating>

## Coverage
- **Read:** units U1–U4 (all), plus beyond the diff: <callers of X, the schema, the config>.
- **Lenses:** <which ran on which units; any that ran inline without a subagent>.
- **Ran:** <tests or reproductions run, with result; static tools; CI status read>.
- **Not reviewed:** <generated files, binaries, a skimmed unit, a lens skipped — and why>.
- **History signals:** <ran | skipped: why>.

## Recommendation
**<Approve | Approve with nits | Request changes | Needs discussion>** — <one sentence on why,
pointing at the findings or questions that decide it>. This is a recommendation. Approval and
merge are yours.

<Handoff line — see SKILL.md.>
```

**Quick tier: the short report.** Keep Claim, Findings, Questions and Recommendation as above.
Collapse Risk map to one line (`Risk: medium — new rule on every submit; wall clock; per-account
config`). Collapse Coverage to two lines: what was read and ran, and what wasn't. Leave out
"What's good" unless there's something specific worth repeating.

### Re-review template

```markdown
# Re-review — <PR> @ <new sha> (previous: <old sha>)

| Finding | Was | Now | Note |
|---|---|---|---|
| PR-1 | blocker | fixed | test `test_zero_percent` added and fails on the old code |
| PR-2 | major | partly fixed | call site in jobs/ still passes the old shape |
| PR-3 | minor | withdrawn | the guard is in the middleware (src/mw.ts:12) — my error |
| PR-4 | major | deferred | tracked as #482 |

## New findings in the fix delta
### PR-5 · major · bug · `…`   <new ids only; never reuse>

## Recommendation
<same rule as the first review>
```

Finding IDs (`PR-1`, `PR-2`…) are stable across rounds and never reused. A new defect gets the next
unused number.
