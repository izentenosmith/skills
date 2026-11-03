# Comments — Writing a Finding Someone Will Act On

> A review is only as good as the comments the author reads. 34.5–44.5% of review comments in
> industrial studies were judged not useful (ACR p.11). The ones that land state the problem, why
> it matters, and what to do instead, in language about the code (ECR; R29, R30). See
> [theory.md](theory.md).

---

## 1. The shape of a comment

Every finding, whether posted inline or listed in the report, has five parts in this order:

```
<label> <one-line claim about the code>

<Why it matters: the failure scenario (inputs/state → wrong result) or the concrete cost
(what the next change has to touch, what a reader will misread, which rule it breaks).>

<Evidence: the quoted line(s), the caller, the history signal, the rule. Enough that the
author can check the claim without re-deriving it.>

<Suggestion: the fix or the alternative, as specific as you can make it. A suggestion block
only when committing it resolves the finding completely.>
```

A worked example:

```
blocker: `apply_discount` charges the full price when `percent` is 0.

`if (!percent) return price` treats 0 as "no discount given" and skips the rounding path, so a
0% promotion returns the unrounded price: 19.999 is charged as 19.999, not 20.00.

src/pricing.ts:42 — `if (!percent) return price;`
Callers pass 0 from `promo.percent ?? 0` (src/checkout.ts:88).

Check for absence explicitly: `if (percent === undefined) return round(price)` — and add a test
for percent = 0.
```

## 2. Labels

Open every comment with a label, so the author can triage without reading closely:

| Label | Means | Blocks the recommendation? |
|---|---|---|
| `blocker:` | Must change before merge. A bug, security issue or data risk with a real scenario | Yes |
| `major:` | Should change before merge. A significant defect or cost, a missing test for new behaviour, a clear rule violation | Yes, unless the author defers it with a tracked issue |
| `minor:` | Worth changing. An evolvability defect with a stated cost, a clarity defect | No |
| `nit:` | Optional. Polish. Grouped into one line in the report | No |
| `question:` | You can't tell whether it's a defect without the author's intent. Ask, and say what the answer changes | No, until answered |
| `praise:` | Something done well that's worth repeating. Specific, never filler | — |

Severity anchors for the first four are in [report.md](report.md#severity).

## 3. Rules

- **About the code, never the author.** Write "this function returns…", not "you forgot…". No
  "obviously", "just", "simply", or "why would you…". A finding on hard code says the code is hard,
  not the author careless (BKS p.97–101; R29).
- **State the problem and the solution** (ECR). A comment without a suggestion is a complaint. If
  you can't suggest a fix, say what you'd need to know to suggest one.
- **Give the evidence, not your reasoning journey.** Quote the line, name the caller, show the
  input. Leave out "at first I thought…".
- **Ask when you don't know.** `question:` is for intent you can't recover from the code: "Is
  `retries = 0` meant to disable retries, or to use the default? The client treats 0 as 'use
  default' (lib/http.ts:30)." A question that changes nothing whatever the answer is noise (ECR:
  "Use: Question").
- **Separate taste from defect.** If it's your preference and no rule or cost backs it, don't post
  it. If it's a convention, quote the rule (lens P).
- **One comment per issue.** If the same defect appears in five places, post it once with the list
  of locations, and don't repeat it five times.
- **Suggestion blocks only when they fully fix it.** A committable suggestion that needs follow-up
  steps is a trap. For multi-site or structural fixes (six or more lines, several locations),
  describe the fix in prose instead.
- **Say what a suggested fix changes and what it leaves alone**, so the author can audit it (ACR
  p.15, p.21; R28).
- **Escalate, don't lecture.** A design disagreement becomes a "let's chat" in Questions, not a
  three-paragraph comment (ECR: "Use: Let's chat").
- **Praise sparingly and specifically.** "The `Clock` seam here makes the expiry test
  deterministic. Worth copying in `billing/`" teaches. "Nice work!" doesn't (ECR: "Compliment").
- **Put context into the code.** If you needed the author to explain a workaround, the fix is a
  comment or a test in the code, not an answer in the thread (BKS p.29; R31).

## 4. Usefulness filter: run it on every comment before it ships

Drop or rewrite any comment that fails one of these (ACR p.11, p.21–22):

1. **Actionable?** Can the author tell exactly what to change, or what to answer?
2. **Justified?** Does it state a scenario or a cost, not just "this is bad"?
3. **Verified?** Is it CONFIRMED or PLAUSIBLE, with the line quoted, rather than a hunch?
4. **Not the linter's?** Would tooling catch it? If so, drop it, or make it one "add a rule" process
   finding.
5. **In scope?** Is it about the diff, or a function the diff touches?
6. **Respectful?** Would you say it to a colleague you respect, face to face?

A naming complaint with no alternative, a "consider refactoring" with no target, and a "this could
be cleaner" with no cleaner version all fail check 1. Rewrite them or drop them.

## 5. Posting to a platform

When posting is in scope (see [SKILL.md](SKILL.md#posting-and-fixing-only-when-asked)):

- One inline comment per unique finding, anchored to the most specific line.
- Link code with the **full commit SHA** and a line range with a line of context either side:
  `https://github.com/<owner>/<repo>/blob/<full-sha>/<path>#L<start>-L<end>`.
- Findings with no line of their own, such as process, alignment or missing files, go in the
  summary comment. The intent check and the coverage statement go there too.
- Never submit an approval or a "request changes" verdict on the platform unless the user asked
  for exactly that. The recommendation goes in the summary text.

## 6. Receiving pushback

When the author disagrees on a re-review:

- **They show the code handles it.** Withdraw the finding, say so plainly, and record it as
  `withdrawn`. Withdrawn is different from fixed (BKS p.156).
- **They accept the risk.** Record `deferred` with their reason, and recommend a tracked issue
  (BKS p.153). Don't re-raise it unless the code changes.
- **It's a disagreement on taste.** Let it go. Taste never blocks.
- **It's still a blocker.** Restate the scenario more concretely: a test, a reproduction, the
  input. Don't restate it more loudly. Then leave it to the human reviewer to decide.
