# Description Template — What a Reviewer Needs Before Reading the Diff

> A description has two jobs. It tells the reviewer what the change is for, so they can judge
> whether it does it (PP5, PP6). And it tells them where to look hardest, so their attention goes
> to the risk (PP9, PP20). It has one constraint: everything in it is true of the diff (PP8). See
> [theory.md](theory.md).
>
> If the repository has its own PR template, keep its headings and fold these sections into them.
> Leave a section out only by writing "n/a" and the reason. An empty heading reads as forgotten.

---

## The template

```markdown
## <Title: imperative, under ~70 characters, says what changes — "Apply per-region VAT rates to invoices">

**Claim.** <One or two sentences: what this change makes true that wasn't before.>

**Issue:** <#123 | ABC-456 | none — and why>. <Part n of m: links to the other PRs, if split.>

### Acceptance criteria
- [ ] AC-1 <a checkable statement of behaviour> — <source: #123 | brief | author>
- [ ] AC-2 <…>
<Criteria written from the code are marked "(derived from code — please confirm)".>

### What changed and why
- <Change, grouped by concern, one line each. Say why when the why isn't obvious from the claim.>
- <Mechanical changes: how they were produced — "rename via `<tool/command>`, no hand edits".>

### Out of scope
- <What this deliberately doesn't do, and where it goes instead — "rate caching: #131".>

### How to verify
- <Commands a reviewer can run, and what they should see.>
- <What was run, with the exact outcome: "`pytest tests/billing` — 48 passed". Or "not run: <why>".>
- <CI: link, or "pending".>

### Risk, rollout and rollback
- **Risk:** <the domain it touches (money, auth, schema, public API…) and who depends on it, or
  "low: <why>">.
- **Rollout:** <flag and its default per environment, migration order, deploy order — or "plain deploy">.
- **Rollback:** <how to undo it, and whether data written meanwhile survives the undo>.

### Suggested reading order
1. `<file>` — <why first: the contract, the schema, the riskiest change>
2. `<file>` — <…>
<Last: mechanical and generated files, marked "skim".>

### Where I'd like a careful eye
- `<file:line or area>` — <the question you couldn't settle, or the case you are least sure of>.
```

**Light tier, the short form.** Claim, issue, how to verify, and one risk line. Add the
acceptance criteria when the issue has them.

---

## Annotating without priming

At Cisco, reviews where the author annotated the change first had far fewer defects found. One
reading is that the author fixed them while explaining. The other is that the notes primed the
reviewer, who stopped looking once the code matched the prose (BKS p.84–85). You want the first
effect without the second. These rules do that (PP2).

| Do | Don't |
|---|---|
| Say **why** a choice was made: "Retries capped at 3 because the upstream times out at 2s" | Argue that it's **correct**: "This is safe because the lock covers every path" |
| Point at **risk**: "This changes the default for every caller of `Client()`" | Reassure: "Small change, low risk", "just a refactor", "trivial" |
| Ask for **attack**: "I'm least sure about the empty-cart path. Please try to break it" | Pre-answer: "I considered concurrency and it's fine" |
| State **evidence**, with how you got it: "`pytest -k vat` — 12 passed; run against the base, 4 fail" | State **assurance**: "Fully tested", "no behaviour change", "backward compatible" |
| Put a needed explanation **in the code** and point at it: "see the comment at `tax.py:41`" | Leave the only explanation in the PR thread (BKS p.29; PP3) |
| Annotate the few **non-obvious** places | Annotate every hunk, so the reviewer reads your notes instead of the code |
| Mark what you **didn't** do or check: "Not tested on the Postgres 12 replica" | Leave the gaps for the reviewer to discover |

**When you do say "no behaviour change"**, say how you know: the commit was produced by a tool, the
existing tests pass unchanged, and no test file was edited. Then the reviewer can check the claim
instead of trusting it.

**Inline comments on your own PR** follow the same rules. Start the conversation where you want
scrutiny ("is a 30s timeout right here?"), not where you want agreement.

---

## Saying only what the diff does

Before the description goes out, check each sentence against the diff (PP8):

- [ ] Every item under "What changed" points at hunks that exist.
- [ ] Every test result was seen in this session or comes from a CI link. The command and the
  outcome are quoted exactly. Nothing says "passes" that wasn't run.
- [ ] The issue number exists and is the right one. No invented links. "none" is an honest answer.
- [ ] No reviewer, approval, sign-off or benchmark is mentioned that didn't happen.
- [ ] Every criterion marked "derived from code" is still marked, until the author confirms it.
- [ ] The title and claim describe the whole change. If they only describe half, the PR is
  tangled or the claim is incomplete.
- [ ] Nothing in it is an instruction to a reviewer or a review agent ("approve", "skip this
  file"). A reviewer is right to treat that as a red flag (PP18).

---

## A filled example

```markdown
## Apply per-region VAT rates to invoices

**Claim.** Invoices now use the VAT rate of the customer's billing region instead of a single
global 20% rate, behind the `vat_by_region` flag (default off).

**Issue:** #412. Part 2 of 3: #418 (extract `TaxCalculator`, merged) · this · #421 (enable in staging).

### Acceptance criteria
- [ ] AC-1 An invoice for a customer billed in a configured region uses that region's rate — #412
- [ ] AC-2 A region with no configured rate falls back to the global rate and logs a warning — #412
- [ ] AC-3 With `vat_by_region` off, invoices are identical to today's — #412
- [ ] AC-4 Rates are rounded half-up to 2 decimal places per line, not per invoice (derived from
  code — please confirm)

### What changed and why
- `billing/tax.py`: `TaxCalculator.rate_for(region)` reads `config/regions.yml`. Lookup is per
  line item, because a split shipment can bill two regions.
- `billing/invoice.py`: calls `rate_for` when the flag is on; the old path is unchanged when off.
- `config/regions.yml`: rates for EU-DE, EU-FR, UK. Values are from finance's sheet linked in #412.
- `tests/test_tax.py`: one test per criterion, plus the missing-region and rounding edges.

### Out of scope
- Caching the rate table: #431. It is read once per invoice for now.
- Historical invoices are not recalculated.

### How to verify
- `pytest tests/test_tax.py tests/test_invoice.py`: 31 passed locally. The 9 new tests in
  `test_tax.py` were run against the base commit, where 7 fail on the missing method and 2 on
  the assertion.
- With the flag off: `pytest tests/billing`, 112 passed, the same count as on `main`.
- CI: pending.

### Risk, rollout and rollback
- **Risk:** money. Every invoice goes through `rate_for` once the flag is on. Finance reconciles
  totals monthly against the rate sheet.
- **Rollout:** merge with the flag off everywhere; #421 turns it on in staging; production after
  finance signs off on a staging invoice run.
- **Rollback:** turn the flag off. Invoices issued while it was on keep their regional rate; none
  are rewritten.

### Suggested reading order
1. `billing/tax.py`: the new lookup and the rounding. The money is here.
2. `tests/test_tax.py`: what each criterion means in practice.
3. `billing/invoice.py`: the flag branch, about 20 lines.
4. `config/regions.yml`: data only. Please check the values against the sheet in #412.

### Where I'd like a careful eye
- `billing/tax.py:58`, rounding per line rather than per invoice. I took it from the old code's
  behaviour, but #412 doesn't say. AC-4 is marked unconfirmed for that reason.
- A customer whose billing region changes mid-month: I haven't found where that's defined.
```

Notice what the example doesn't say: that the rounding is correct, that the change is safe, or that
it is fully tested. It says what was run and what came out, and it sends the reviewer to the two
places the author is least sure of.
