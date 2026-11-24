---
name: threatmodel
description: Reviews a system's security design, or designs or proposes one — assets, adversaries, trust boundaries, data flows and key management. Review mode audits an architecture or threat model with a 0–10 score; Design mode writes threat-model.md (data flows, STRIDE per boundary, risk register); Propose mode sequences risk treatment. Use for threat modelling, security design review, "what could go wrong with this design", or before building anything touching money, identity, keys or personal data.
---

# 🎯 threatmodel

A threat model answers four questions in order: **what are we protecting, from whom, where can
they reach it, and what stops them** — and then the fifth one that most models skip: **how do we
know it works.** Anderson's framing is that every dependable system needs a **policy** (what must
hold), a **mechanism** (what enforces it), **assurance** (evidence the mechanism works) and an
**incentive** (someone motivated to keep it working). Almost every security failure is a missing
one of those four. This skill grades designs against that model, writes the model, and sequences
the treatment.

## When NOT to use

- Reviewing the code for vulnerabilities → `appsec`.
- Locking down the hosts and cloud accounts → `hardening`.
- Network zones and flows in depth → `netdesign`.
- Design questions that are not about security → `architect-deep-dive`.
- A security exposure happening now → `incident-fix`.

## Where this fits

Three security skills, one per layer:

- **threatmodel** (this skill) — *what* to protect and from *whom*: assets, adversaries, trust
  boundaries, the security policy a system must enforce
- [appsec](../appsec/SKILL.md) — whether the **code** enforces it: injection, authn/authz, sessions,
  crypto use, dependencies
- [hardening](../hardening/SKILL.md) — whether the **platform** the code runs on is locked down:
  hosts, accounts, networks, storage, backups, monitoring, governance

The threat model comes first when there is one to write: it tells appsec which flows to read
hardest and tells hardening which assets are crown jewels. Neighbours outside the family:
`netdesign` owns zones and flows in network depth;
`pipelines` owns the CI/CD trust chain;
`architect-deep-dive` resolves the non-security
design questions a threat model surfaces.

Reference docs, all in this folder:

- [theory.md](theory.md) — the principles every finding cites (S1–S27)
- [review-rubric.md](review-rubric.md) — per domain: 🟢 well done, 🔴 anti-patterns (what, why,
  detect, severity), checklist criteria
- [detection-signals.md](detection-signals.md) — phrases, structures and greps in design artefacts
  per anti-pattern, with confidence tags
- [design-patterns.md](design-patterns.md) — DFD and trust-boundary conventions, STRIDE per element,
  threat tree, FMEA, hazard × mechanism matrix, adversary catalogue, access-control model chooser,
  protocol patterns, risk register, requirements traceability, the `threat-model.md` skeleton
- [scoring.md](scoring.md) — severity, confidence, the 0–10 formula, the gate, templates
- [proposal.md](proposal.md) — treatment decisions, sequencing, which skill each item goes to

---

## 📐 Pick the mode

Say which one up front, and the tier within it.

| Mode | Input | Output |
|---|---|---|
| **Review** | An architecture, design doc, ADRs, an existing threat model — or a repo to reconstruct one from | Findings, per-domain scores, the gate. Changes nothing. |
| **Design** | Requirements, a design to model, or a review to correct | `threat-model.md`: system definition, assets, adversaries, DFD with trust boundaries, threats, hazard × mechanism matrix, risk register, security requirements with traceability |
| **Propose** | A review and/or a threat model | `proposal.md`: a treatment decision per risk and a sequenced plan, each item routed to the skill that does it |

**Calibration tier** — pick once, up front, from what the system can lose:

| Tier | The system | Run |
|---|---|---|
| **Lightweight** | One feature or service, internal or public data, no money, keys or safety | DFD, STRIDE per trust boundary, top threats, risk list, requirements for the change |
| **Standard** | A product or a service with personal/confidential data, auth, or integrations | Everything in Design except FMEA; threat tree for the top 3 undesired outcomes |
| **High-assurance** | Money, identity providers, key custody, safety, regulated data, anything irreversible | Everything: threat tree + FMEA + meet-in-the-middle + hazard × mechanism matrix, and a hostile review by someone who didn't build it |

**Two rules that keep the tier honest:** calibrate once, not domain by domain; and anything that
moves money, grants identity, holds keys or can't be undone is high-assurance no matter how small
the diff.

Review tiers:

| Tier | When | Run |
|---|---|---|
| **Change review** | A design change or ADR, not a whole system | R1 for the touched boundaries, R3 against the change; findings without a score |
| **Domain review** | One concern ("is our authorisation model sound?") | R1–R3 for that domain |
| **System review** | One system or product | R1–R4 |
| **Portfolio review** | Several systems sharing identity, keys or networks | R1–R4 per system, then R5 |

---

## 🔎 Review

The review **does not prescribe**. It produces evidence, the principle each gap violates, a model
of the system and a number. Treatment belongs to Design and Propose.

Scope is **design evidence**: architecture docs, diagrams, ADRs, sequence diagrams, OpenAPI/AsyncAPI
specs, IaC, runbooks, an existing threat model (Threat Dragon, pytm, Threagile, Microsoft TMT
files), and — where the docs are thin — the code, read to reconstruct what the design actually is.
**Never attack, scan or probe a live system** in Review. What the design implies but only runtime
can confirm is 🔬.

### R1 — Inventory (reconstruct the model)

- [ ] **Redact first.** Design docs and IaC carry endpoints, keys and credentials. Never copy a
  secret into an output — record the *kind* and the location.
- [ ] **System definition**: components, *and* the people around them — operators, admins, support
  staff, customers, partners, recovery and onboarding flows (S2). A model that lists only software
  has already missed the help desk.
- [ ] **Asset register**: what an adversary would want — data (by class), money, identity, keys,
  availability, reputation, **metadata** (who talks to whom, when) — each with its owner (S2, S16).
- [ ] **The DFD**: external entities, processes, data stores, flows, and **trust boundaries**. If no
  diagram exists, reconstruct one from code/IaC/docs and label it *reconstructed*. This diagram is
  the review's spine; boundaries, protocols and the gate read it.
- [ ] **Boundary-crossing table**: every flow that crosses a trust boundary → how the caller is
  authenticated, where authorisation is decided, how the channel is protected, what input
  validation happens. Blank cells are findings waiting to be confirmed.
- [ ] **Adversaries as documented** (or "none stated"), **protected operations**, **protocol and key
  inventory**, **serious hazards** (the outcomes the owners couldn't tolerate).
- [ ] **Counts per domain** — they weight the score ([scoring.md](scoring.md)).
- [ ] **Source version**: the commit or document version every finding cites. **Output location**:
  the repo's convention, else `analysis/threatmodel/`. Never write inside this skill's folder.

### R2 — Read the existing model and tools' output

An existing threat model, a tool report (pytm, Threagile, Threat Dragon), a pen-test report or a
previous review is **evidence, not the review** — check its age against the architecture's: a model
older than the last boundary change is stale (S24). Record what existed, its date, and whether the
current system still matches it.

### R3 — Evaluate each domain

One domain, one section of [review-rubric.md](review-rubric.md): **scope**, **adversaries**,
**boundaries**, **policy**, **protocols**, **resilience**.

- [ ] **Walk the domain's 🔴 anti-patterns** against every in-scope object, using
  [detection-signals.md](detection-signals.md) to find candidates in the artefacts and reading each
  in context. A phrase is a candidate, not a finding: "the internal network is trusted" in a
  section titled *Rejected options* means the opposite.
- [ ] **Every finding carries six things**: ID, object, anti-pattern, **confidence** (✅/⚠️/🔬),
  **the theory it violates** (S-N), **severity**, and **evidence** (`doc:section`, `file:line`,
  diagram element ID). A finding missing any of them is incomplete.
- [ ] **Silence is a proxy, not proof.** A design doc that doesn't mention revocation is ⚠️ until the
  code or the owners confirm there is none.
- [ ] **Record the 🟢 too.** What the design gets right tells Propose what to keep.
- [ ] **Count per criterion** how many in-scope objects satisfy it.

### R4 — Score and summarize

Apply the formula: `p` per criterion, base, caps, confidence rule. **Show the arithmetic.** Write
`summary.md` from the template: scores, severity tally, 🔬 tally, the DFD, the boundary-crossing
table, the asset register, the adversary model, what works, top findings, systemic issues, and
**each gate condition separately**.

### R5 — Portfolio synthesis

Across systems: capped and uncapped scores; a severity heatmap (system × domain); **shared trust**
— one identity provider, one signing key, one admin group, one network every system trusts — and the
**cascades** it creates (secure components don't compose, S10); themes, each tied to its theory.

---

## 📝 Design

Follow Anderson's method, in this order. Read [theory.md](theory.md) and
[design-patterns.md](design-patterns.md) first. Skip only what the calibration tier says to skip,
and say which.

1. **Scope and goals.** Define the system broadly (components, people, recovery flows, third
   parties); list assets and data classes; write the protection goals as *who may do what to which
   asset* — never "the system is secure" (S1, S2). List assumptions and open questions; never
   silently promote an assumption into a constraint.
2. **Eliminate hazards by design first.** Before adding any control, ask which hazards can be
   removed: data you don't need to hold, a central key store that needn't exist, a privileged
   component that could be split (S3). A removed hazard needs no mechanism, no test and no owner.
3. **Adversaries.** Opponent classes and grades that matter for this system, their capabilities,
   what they can obtain *legitimately* (sign up, call support, get hired), and which attacks scale
   (S5–S7). Name the grade you design against.
4. **DFD and trust boundaries.** Draw it ([design-patterns.md](design-patterns.md) §1); fill the
   boundary-crossing table; keep the trusted computing base small and say what's in it (S4, S9).
5. **Top-down threat tree** per undesired outcome: root = the outcome, children = immediate causes,
   recurse; mark shared branches — one fix that cuts many paths (§3).
6. **Bottom-up FMEA** (high-assurance): for each component, the effect of its failure — accidental
   *and* malicious — on the mission (§4).
7. **Meet in the middle**: trace attack paths across trust boundaries and apply **STRIDE per
   boundary crossing** (§2).
8. **Hazard × mechanism matrix**: every serious hazard needs **two independent mechanisms**; a row
   with one is a single point of failure (S22, §5).
9. **Policy and access-control model**: choose the model deliberately — RBAC, ABAC, capabilities,
   Bell-LaPadula/Biba/type enforcement, Clark-Wilson, Chinese Wall — and the separation-of-duty,
   dual-control and break-glass rules (S13, S14, §7).
10. **Protocols and keys**: authentication and authorisation protocols, freshness, transaction
    binding, key lifecycle, revocation, time (S17–S21, §8).
11. **Quantify cautiously**: seriousness × likelihood on 1–5 each, an owner per risk; annual loss
    expectancy only where real data exists — say which numbers are data and which are guesses (§9).
12. **Security requirements**, traced threat → objective → requirement → test, each specific
    enough to build and test (§10).
13. **Downstream use and re-run triggers**: which flows appsec reviews hardest, which assets
    hardening treats as crown jewels, what a pen test targets; and the events that force a re-run
    (a new trust boundary, a new data class, a new adversary, a protocol change, an incident).

`threat-model.md` follows the skeleton in [design-patterns.md](design-patterns.md) §11. Diagrams as
Mermaid or a draw.io file the repo already uses; IDs on every element, threat, mechanism and
requirement so the traceability table can reference them.

---

## 📦 Propose

Follow [proposal.md](proposal.md). Every risk gets a decision — **eliminate by design**,
**mitigate**, **transfer**, or **accept** with an owner and an expiry. Sequence: containment of
anything live and exploitable → eliminate hazards by design → boundary controls → detection →
assurance. **Exploitability, not domain, decides the step:** a live weakness on a privileged path
(SMS MFA for admins, a fail-open fallback on money) gets an interim containment in the first window
even when its full fix belongs to a later phase. Each item is routed: code to [appsec](../appsec/SKILL.md), platform to
[hardening](../hardening/SKILL.md), CI/CD to `pipelines`,
network to `netdesign`.

---

## 🛑 Stopping rule

**Review** stops when: the DFD and boundary-crossing table cover every in-scope component and
crossing; every in-scope domain has an evaluation with coverage stated; every finding has its six
fields; every score shows `p`, base and cap; every 🔬 flag is listed by name; the gate is stated
condition by condition.

**Design** stops when: every asset has an owner; every boundary crossing names its authentication
and authorisation decision; every serious hazard has two independent mechanisms or an accepted risk
with an owner; every requirement traces to a threat and has a test; open questions are listed with
the decision each blocks.

**Propose** stops when every risk has a decision, every Critical/High has a sequenced step, and
every step names the skill and owner that carries it.

Then stop. There is always another threat to enumerate. **A threat that no mechanism, test or
decision would change is a line for its own sake** — model the attacks the named adversaries can
afford, not every attack physics allows.

---

## Subagents — optional

Worth it for a **portfolio** or a system too large to hold at once. In Review, delegate R1 per
system or per subsystem — reconstructing the DFD and boundary-crossing table from its docs and code,
read-only, returning the inventory and candidate findings in the six-field shape with "could not
determine" per field. **Keep the adversary model, scoring, the gate and the synthesis in the main
thread.** In Design, a fresh-context delegate is valuable for one thing: a **hostile review** of the
finished model by someone who didn't write it (S24). The threat tree, the matrix and the
requirements are one set of decisions and stay in one head.

**Dispatch contract.** Give each delegate the prior (mode, tier), the target (which components it
owns, and that the rest are covered), the context it cannot infer (asset classes, which data is
regulated, the adversaries in scope), the return shape, and "report conclusions, not file excerpts".
Delegates stay read-only and never touch a live system.

---

## Rules of Engagement

1. **Never attack or probe a live system.** Review reads artefacts; anything only runtime can prove
   is 🔬. A pen test is a separate, authorised engagement.
2. **Never echo a secret.** Record the kind and location; recommend rotation, not just deletion.
3. **Every finding cites a principle.** S-N from [theory.md](theory.md), or it's taste.
4. **People are in the system.** Operators, support, customers and recovery flows are modelled
   like components.
5. **Name the adversary.** A threat without an adversary who can afford it is noise; an adversary
   nobody named is the one that gets in.
6. **Generic, not branded.** No organisation's names, products or internal tooling in the model's
   reusable parts — use placeholders.
7. **Review doesn't prescribe; design doesn't build.** Each mode stops at its own deliverable.

## Handoff

> Reviewed `<system>` at `<version>`: score `<x>` (`<band>`), gate `<pass/fail — failing
> conditions>`. `<n>` Critical, `<n>` High. DFD, boundary-crossing table and adversary model in
> `analysis/threatmodel/summary.md`.
> Next: **Design** to model `<domains>`, then **Propose** for treatment; code-level checks of the
> named flows go to **[appsec](../appsec/SKILL.md)**, crown-jewel assets to
> **[hardening](../hardening/SKILL.md)**.
