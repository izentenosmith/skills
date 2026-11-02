# Scoring — Severity, Confidence, the 0–10 Formula, Templates

> How a threat-model review is graded and written down. **Rubric version: `v1.0`.** Every output
> records the rubric version it was graded against and the version of the design evidence it read
> (commit, document revision, diagram date). Each finding names the principle it violates from
> [`theory.md`](theory.md) (S-N). A finding that asserts a gap without naming the principle is
> incomplete — a gap without a principle is taste.
>
> The formula is the same one the database, networking, infrastructure and other security skills
> use, so a 7.4 means the same thing everywhere.

## Severity taxonomy

Severity reads the **asset** at stake and the **adversary** who can reach it. The same missing
replay protection is Critical on a payment instruction and Low on a "like" button; say which asset
you graded against.

| Severity | Meaning | Calibration anchors |
|---|---|---|
| **Critical** | The design lets a named, realistic adversary reach a high-value asset now, or lets one failure cause an irreversible loss | A boundary crossing from an untrusted zone to a high-value asset with **no** authentication or authorisation decision; an irreversible high-value action (moving money, deleting production, exporting a key, granting admin) gated by a single credential and nothing else; authentication by a static secret or identifier over an observable channel; a key shared fleet-wide or derived from a public identifier protecting high-value assets; account recovery that bypasses every login factor; money or ledger state mutable without a balancing invariant |
| **High** | A broad gap in isolation, authorisation, protocol or recoverability | No adversary model, or "hackers" only, for a system holding confidential data; "internal means trusted"; authorisation only in the UI or gateway; one role spanning contexts with whole-record access; SMS as the second factor for high-value actions; long-lived bearer tokens with no revocation path; no key lifecycle or compromise recovery; ECB, nonce reuse or distinguishable decryption errors in the design; backups reachable from production credentials; break-glass access with no alert; fail-open on an authorisation dependency; a serious hazard covered by one mechanism |
| **Medium** | Controlled risk, or debt that becomes High as the system grows | A threat model older than the last boundary change; a DFD missing people, recovery flows or third parties; STRIDE applied per component but not per boundary crossing; metadata and inference ignored; no abusability analysis for shared accounts or devices; risk numbers with no stated basis; a threat "mitigated by monitoring" with no owner or response time; no coordinated-disclosure route |
| **Low** | Notation, traceability, documentation | Elements without IDs; requirements not linked to threats; inconsistent naming between diagram and text; missing re-run triggers |

## Quality scale (per criterion)

- 🟢 **Well done**: meets the criterion; matches theory and current practice.
- 🟡 **Acceptable / watch**: works, but carries security or assurance debt.
- 🔴 **Not well done**: violates the criterion. A gap, an anti-pattern, or a theory failure.

## Detection confidence

A design artefact can prove what it says; it can only suggest what it leaves out. Every anti-pattern
carries one of three tags.

| Tag | Meaning | Counts toward score? |
|---|---|---|
| ✅ **decidable** | Provable from the evidence in hand: the diagram shows a flow from the internet to the database with no auth annotation; the doc states "SMS OTP" for wire approval; the OpenAPI spec has `security: []` on a state-changing operation; the code reconstructing the design shows a single approver for deletion | Yes. A confirmed gap. |
| ⚠️ **proxy** | A signal that needs judgement: the doc is **silent** about revocation, rate limiting or insiders; "should"/"will" language without a mechanism; a role name suggesting broad access; a model's date older than the architecture's | Yes, at reduced weight (below) |
| 🔬 **needs-data** | Needs runtime or organisational evidence you don't have: whether the implementation matches the design, whether the dual-control procedure is followed, whether alerts reach anyone, who actually holds key shares | **No.** Recorded as a flag, never scored. |

Code read to reconstruct the design is evidence: a missing authorisation call found in the handler
is ✅ for the design's boundary-crossing table. Whether production matches the code is 🔬.

## Scoring model

### Evaluation units

One evaluation per **domain** per system, graded with its section of
[`review-rubric.md`](review-rubric.md):

| Domain | In-scope objects (the weight) |
|---|---|
| scope | assets: data classes, money, identities, keys, availability, metadata — each asset in the register |
| adversaries | adversary classes relevant to the system (opponents × grade, plus insiders and abusers where they apply) |
| boundaries | trust boundaries and the data flows crossing them |
| policy | protected operations and objects (each action on each asset class that the policy must govern) |
| protocols | authentication, authorisation, key-management and other protocol exchanges |
| resilience | serious hazards — the undesired outcomes the owners can't tolerate |

A **system** is the unit the user names. Several systems sharing identity, keys or networks make a
portfolio.

### Per-domain score

1. **Grade each criterion proportionally.** `p` = fraction of in-scope objects that satisfy it.
   - `p ≥ 0.95` → 🟢 (2 pts)
   - `0.50 ≤ p < 0.95` → 🟡 (1 pt)
   - `p < 0.50` → 🔴 (0 pts)

   "In-scope" excludes objects the criterion can't apply to: the transaction-binding criterion
   doesn't apply to a read-only query; dual control doesn't apply to a reversible low-value action.
2. **Checklist base.** `base = (Σ points / (2 × criteria)) × 10`.
3. **Severity caps**, applied after the base (lowest wins): any open **Critical** caps at **2.0**; any
   open **High** caps at **6.0**.
4. **Confidence rule.** Only ✅ and ⚠️ findings affect the grade. ⚠️ alone may grade a criterion 🟡,
   never 🔴. 🔬 never moves the score.

`domain_score = min(base, caps)`, floored at 0, one decimal.

### Per-system and portfolio scores

The **system score** is the mean of its domain scores, weighted by in-scope object count, with the
Critical/High caps re-applied. The **portfolio score** is the mean of system scores, weighted by
total objects, caps re-applied. Report the uncapped mean beside the capped one.

### Bands

| Score | Band |
|---|---|
| 9.0–10 | Exemplary |
| 7.0–8.9 | Good, minor debt |
| 5.0–6.9 | Needs work |
| 3.0–4.9 | Poor |
| 0–2.9 | Critical / unsafe |

### The gate

A design is **good enough** — no treatment proposal is owed — only when all of these hold:

- the capped score is ≥ 9.0;
- no open Critical or High finding remains;
- every serious hazard has **at least two independent mechanisms** in the hazard × mechanism matrix
  (S22);
- every trust-boundary crossing names its **authentication** and its **authorisation decision**
  (S9, S11);
- every risk in the register has an **owner** and a **treatment** (S1, S24);
- 🔬 flags number at most 10% of objects.

State the score-based result and each gate condition separately. A 9.2 whose wire approval rests on
one password is not good enough.

## Triage for large systems

Above **~40 components or ~15 trust boundaries**, don't model everything at one depth:

1. **Rank assets** by what their loss costs and **boundaries** by how untrusted the far side is.
2. **Deep-model** every crossing that touches a crown-jewel asset or an untrusted zone; model the
   rest at DFD + STRIDE depth.
3. **State coverage**: "deep-modelled 9 of 31 crossings (all crown-jewel and internet-facing);
   STRIDE over all 31."

The inventory (assets, DFD, boundary-crossing table) must still cover **everything**: an unlisted
flow into the core is the finding that matters most.

## Theory → domain mapping

| Domain | Primary theory to invoke |
|---|---|
| scope | Four axes (S1); goals and system definition (S2); eliminate hazards (S3); small TCB (S4); models verified against the system (S27) |
| adversaries | Named opponents and grades (S5); attacks that scale (S6); insiders and abusers (S7); predictable human error (S8) |
| boundaries | Compartments and lateral flow (S9); composition (S10); enforce at the right layer (S11); least privilege, confused deputy (S12); one trust domain per component (S26) |
| policy | Access-control model (S13); separation of duty and break-glass (S14); usable defaults (S15); metadata and inference (S16); no circumventable rule or self-grantable role (S25) |
| protocols | Freshness (S17); transaction binding (S18); key management (S19); revocation and time (S20); correct crypto (S21) |
| resilience | Two mechanisms, fail-safe, degraded modes (S22); detection and evidence (S23); continuous hostile assurance (S24); incentives (S1) |

## Templates

### Per-domain evaluation — `analysis/threatmodel/<system>/<domain>.md`

```markdown
# <System> — <Domain> evaluation
> Evaluated against threatmodel/review-rubric.md §<domain> (rubric v1.0).
> Evidence: <docs, diagrams, ADRs, specs, code paths> — as of <commit / revision / date>.
> Tier: <lightweight / standard / high-assurance>. Coverage: <N of M deep-modelled; STRIDE over all M>.

## Findings
| ID | Object | Anti-pattern | Conf. | Theory violated | Severity | Evidence |
|----|--------|--------------|-------|-----------------|----------|----------|
| TM-BND-01 | F7 partner → orders-api | Crossing with no authorisation decision | ✅ | Enforce at the right layer (S11) | Critical | docs/arch.md §4.2; orders/api.py:88 |

## Signal counts
| Anti-pattern | Count |
|--------------|------:|

## Needs-data flags (not scored)

## Checklist
| # | Criterion | Satisfied / in scope | p | Result |
|---|-----------|---------------------:|--:|--------|

**Domain score: <0–10>** (base <b>, cap <c> — reason)
```

### Per-system summary — `analysis/threatmodel/<system>/summary.md`

```markdown
# <System> — Threat-model review summary
> Components: <n> · trust boundaries: <n> · crossings: <n> · assets: <n> · serious hazards: <n>. Evidence as of <version>; rubric v1.0.

## Scores
| scope | adversaries | boundaries | policy | protocols | resilience | **System** |
|---:|---:|---:|---:|---:|---:|---:|

## Severity tally · Needs-data flags
## Asset register (asset → class, owner, why an adversary wants it)
## Adversary model (class × grade → capability, legitimate access, scaling attacks)
## DFD (reconstructed or supplied — say which)
## Boundary-crossing table (flow → authn, authz decision, channel, validation)
## Hazard × mechanism matrix (serious hazards only)
## What is working well
## Top findings (worst first)
## Systemic issues
## Gate (each condition, pass/fail, with the reason)
```

Finding IDs: `TM-<SCO|ADV|BND|POL|PRO|RES>-NN`.
