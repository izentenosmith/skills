---
name: dbpropose
description: Propose changes to a relational database from an audit — a reuse / refactor / rework / rebuild / drop verdict per object, a topology derived from real coupling, a modelled target schema (ER model → table instance diagrams → PostgreSQL 18 DDL by default) with a migration and integrity plan, or an ordered in-place remediation register. Also designs or reviews a new data model from requirements. Use after dbaudit, when planning a database migration, redesign or cleanup, or when a schema needs to be modelled properly before it is built.
---

# 🏗️ dbpropose

## Where this fits

Two database skills, in order:

1. [dbaudit](../dbaudit/SKILL.md) — grades the DDL: findings, scores, summaries, synthesis
2. **dbpropose** (this skill) — decides what to keep, fix, redesign, rebuild or drop, and what the
   database looks like afterwards

**A proposal never runs ahead of its evidence.** Every verdict cites the score and the finding that set
it; every target table is **modelled** — entity, relationships, identifier — before it gets DDL; every
runtime question stays an open 🔬 question instead of being answered by assumption. A redesign drawn
from a skim of the schema is a preference, not a proposal.

Reference docs, all in this folder:

- [proposal.md](proposal.md) — the input contract (how to read an audit), verdict rules, topology from
  coupling, the SQL Server → PostgreSQL 18 translation table, drafting, migration plan, the in-place
  remediation register, and the `target-schema.md` skeleton
- [er-modeling.md](er-modeling.md) — CAP1–CAP4: entities, relationships, attributes, UIDs;
  normalization, recursion, roles, subtypes, arcs, history; mapping the model to tables with Table
  Instance Diagrams; 25 drills
- [physical-design.md](physical-design.md) — the PostgreSQL 18 standard: keys, naming, integrity,
  arcs/subtypes/temporal keys in the engine, types, indexes, collation, where logic lives
- [theory.md](theory.md) — the principles a verdict's rationale cites

---

## 📐 Calibrate the pass

Pick one up front and say which:

| Mode | Input | Produce |
|---|---|---|
| **Migrate** | An audit of the legacy database(s) | `target-schema.md` — Steps 0–6 |
| **Remediate in place** | An audit; the engine stays | `remediation-plan.md` — Steps 0–2, then the register in [proposal.md](proposal.md) Step 6 |
| **Design** | Requirements, interview notes or a domain description — no legacy | A model and target DDL — Steps 4–6 only, the model built forwards from [er-modeling.md](er-modeling.md) |
| **Design review** | Someone else's ER model or schema proposal | Gaps against er-modeling's rules and drills and physical-design's checklist, with severity; no rewrite unless asked |

**No audit, but a legacy database?** Say so and run [dbaudit](../dbaudit/SKILL.md) first. Proposing
verdicts without scores is guessing; the only modes that don't need an audit are *Design* and *Design
review*.

Also state the **target engine** — PostgreSQL 18 unless the user names another; for another engine the
model is unchanged and [physical-design.md](physical-design.md)'s choices are translated.

---

## 📥 Step 0: Read the audit

Follow [proposal.md](proposal.md) Step 0. Confirm the per-file evaluations, per-database summaries,
estate synthesis and 🔬 flags exist, note the rubric and source versions, and **find the capping
finding behind every low score** before reading the score as a verdict — a 2.0 is often one Critical
defect in an otherwise sound schema.

## ⚖️ Step 1: Verdicts

Every object (or object group) gets **reuse / refactor / rework / rebuild / drop**. The **score band
sets the default and findings override it**: an open Critical forces at least *rework*; business logic
in procedures/triggers moves to the application layer; shadow tables, dead and copy schemas drop;
near-dead schemas drop unless a live consumer is confirmed. Decide **structure, data and logic
separately** — "structure: rework, data: migrate with cleanup, logic: reimplement in the app" is a
normal answer. Name the overriding finding wherever the verdict departs from the band.

## 🗺️ Step 2: Topology from evidence

Build the coupling graph from the audit's cross-database edge list (or collect it — [proposal.md](proposal.md)
Step 2 has the greps), cluster tightly coupled domains into shared schemas, keep loose ones as separate
schemas in one database, drop dead schemas, fold near-dead survivors into their consumer. Output the
**schema map** with the edge counts that justify each grouping. Don't inherit the legacy folder layout
as the answer.

*(Remediate in place: skip to the register now — [proposal.md](proposal.md) Step 6.)*

## 🧩 Step 3: Translation decisions

Adopt or deviate from the translation table in [proposal.md](proposal.md) Step 3, per domain, and
record each deviation with its reason.

## 🧠 Step 4: Model before DDL

For every rework/rebuild domain:

- [ ] **Start from the recovered model** in the audit notes (or recover it — [er-modeling.md](er-modeling.md)
  §A0). Rebuilds re-derive the model from requirements; the legacy model is reference only.
- [ ] **Correct it with CAP1–CAP2**: entities that pass the tests, two-way relationship sentences with
  real names, M:M resolved, derived attributes removed, UIDs that meet the criteria (no intelligent
  keys), subtypes/roles/arcs/recursion/history made explicit — history only where the user asked for it,
  with gaps, overlaps and future-dated values decided.
- [ ] **Run the CAP4 drills** whose traps apply, and say which passed.
- [ ] **Map it with CAP3's six steps** and document the core tables as **Table Instance Diagrams** —
  key types, `NN`/`U` marks, sample rows drawn from the legacy data.

A target table nobody can phrase as entity, relationships and UID is not designed yet.

## 🏛️ Step 5: Physical design

Apply [physical-design.md](physical-design.md) (or its translation for another engine): surrogate keys
with natural keys as `UNIQUE`, every real relationship as an FK, `NOT NULL` from the model's mandatory
marks, explicit arcs with exclusivity `CHECK`s, subtype mapping with enforced subtype columns, temporal
keys for history, one collation, FK indexes, logic placed — invariants as constraints, set-based data
operations as views/functions, business rules to the application. Express it as DDL grouped by the
Step 2 schema map.

## 🚚 Step 6: Migration & open questions

Follow [proposal.md](proposal.md) Step 5: load with constraints not enforced, clean (magic values →
`NULL`, collation and type normalization, orphan resolution, repeating groups unpivoted into child rows,
generic-arc ids split into explicit FKs, shadow tables deduped to their authoritative sibling), then
validate. **List every unresolved 🔬 flag as an open question by name**, with what it would change.

Write the result in the `target-schema.md` skeleton from [proposal.md](proposal.md).

---

## 🛑 Stopping rule

Stop when all hold:

- [ ] Every object in scope has a verdict (groups allowed) on all three axes, with the overriding finding
  named where it departs from the score band.
- [ ] The schema map cites coupling evidence for every grouping.
- [ ] Every target domain has its corrected model, the drills it passed, and TIDs + DDL for its **core**
  tables — not every column of every table.
- [ ] *Remediate in place:* every register row cites its finding, has a patch, a risk and a rollback,
  and is ordered Critical-first and by dependency.
- [ ] Every 🔬 flag is resolved by the user or listed as an open question.

Then stop. The proposal is **tentative by construction** until its 🔬 questions are answered on a live
instance; polishing DDL for tables whose shape depends on an unanswered data question is effort spent
on a guess. Say what would make it final, and hand off.

---

## Subagents — optional

Useful on an estate, at the edges only.

**Delegate read-only evidence work** — collecting the coupling edge list from the dumps, or recovering
the model of one domain from its tables (§A0) — one delegate per domain, dispatched together. Keep the
**verdicts, the topology, the modelling decisions and the DDL** in the main thread: they are judgements
that must be consistent across domains, and a schema map assembled from independent opinions has
seams exactly where the coupling was.

**Dispatch contract.** Give each delegate the **prior** (the audit's headline and which domains exist),
the **target** (which domain or files it owns), the **context it cannot infer** — paste §A0 of
er-modeling and the relevant audit findings inline — the **return shape** (entities with one-line
descriptions, relationship sentences, PK/UID assessment, suspected subtypes/arcs/history, each with the
file:line it came from; "could not determine" where the DDL is silent), and *"report conclusions, not
file excerpts."* Delegates stay **read-only** and propose nothing.

---

## Rules of Engagement

1. **Evidence first.** No verdict without the score and finding behind it; no legacy proposal without
   an audit.
2. **Findings beat scores.** Read the cap before the number.
3. **Model before DDL.** Entity, relationships, UID — then tables, then types.
4. **Topology from coupling**, not from the folder layout you were handed.
5. **History only on request**, with gaps, overlaps, future values and retention decided out loud.
6. **Open questions stay open.** A 🔬 flag is never resolved by assuming the convenient answer.
7. **Propose, don't apply.** Never alter a database or run a migration; every patch is for review.

## Handoff

> Proposal for `<D>` databases from audit `<rubric v1.1, source commit/date>`: `<n>` reuse ·
> `<n>` refactor · `<n>` rework · `<n>` rebuild · `<n>` drop. Target: `<k>` schemas in one
> `<engine>` database (from `<e>` coupling edges) — or `<r>` remediation changes, `<c>` Critical first.
> `<q>` open 🔬 questions block a final design.

To build it, run **[architect-deep-dive](../../development/architect-deep-dive/SKILL.md)** on the open
questions and the riskiest decisions, then **[agent-brief](../../development/agent-brief/SKILL.md)** to
turn the migration plan or the register into build slices. State the verdict counts and the open
questions out loud — they are the cost and the uncertainty of what is being proposed.
