# Requirements Dossier — Before the Model

> What dbdesign records before drawing a single entity. All three design phases (er-modeling §A)
> depend on it: entities come from the user views, cardinalities and optionality from the rule
> catalogue, column definitions from the data dictionary, the access design from the access matrix, and
> index and partitioning choices from the volumetrics. A requirement says **what the data is**, not how
> it is processed.

## The seven artefacts

### 1. Scope and user views
One row per user group or subsystem: the data it creates, the data it reads, and its source person or
document. Requirements are summarized **across all user groups**, not per person — an integrated view
is what the model has to satisfy. Subsystems that barely touch get their own model, integrated through
the entities they share (er-modeling §A1.2).

### 2. Business-rule catalogue

| Id | Rule (in the business's words) | Kind | Fundamental / policy | Source | Enforcement (tier, mechanism) |
|---|---|---|---|---|---|
| BR-01 | Every order has one customer | structural | fundamental | sales lead | 3 — FK, `NOT NULL` |
| BR-02 | A borrower holds at most one open loan per copy | key | fundamental | library desk | 2 — partial unique index |
| BR-03 | A student carries at most 180 credit points at once | aggregate | policy | registry | 4 — deferred constraint trigger + parent lock |

**Kinds** (theory §7.1): *structural* (relationship cardinality and optionality), *domain* (a value
set or format), *key* (uniqueness, no overlap), *cross-row / aggregate*, *equality dependency* (a
parent must have children; subtype completeness), *temporal* (history, gaps, overlaps, future dating),
*transition* (allowed state changes), *authorization*, *process*. Include legal, regulatory and
ethical constraints (retention, privacy, accounting standards). The enforcement column is filled at
physical design (physical-design §5.3).

### 3. Data dictionary
Per attribute: entity, definition, domain/type, mandatory (`*`) or optional (`o`) and — if optional —
**what NULL means** (theory §3.2), single-valued?, stable over time? (an unstable attribute such as age
is derived — er-modeling §A1.4), history needed?, sensitivity class, example values. One concept, one
definition: the same concept has one name and one domain wherever it appears. The dictionary becomes
`COMMENT ON` statements in the DDL.

### 4. Access matrix
Role × entity × create / read / update / delete, plus column- or row-level restrictions and the
sensitivity classes they protect. It drives physical-design §11.

### 5. Volumetrics and key transactions
Expected row counts and growth per entity; the most frequent queries and updates (the functional
requirements), with their frequency and latency expectations. Indexes and partitioning are chosen
against these, not guessed.

### 6. Assumptions
Every point the design **commits to** without confirmation (`A-nn`): the assumption, why it is the
reasonable reading, the rule or table it shapes, and what changing it would cost. The design is built
on these, so a reviewer must be able to find and overturn each one.

### 7. Open-questions log
Every point the design **does not decide** (`OQ-nn`): the question, the decision it blocks, who can
answer it, and how the schema stays neutral until then (an optional column, no constraint yet).

Assumptions and open questions are **two lists under two headings**, and each item sits in exactly one.
Don't head a section "Assumptions and open questions", and don't list an assumption again as a
question "to confirm". If the design picks an answer, it's an assumption, and confirming it is part of
reviewing it. If the design leaves the point open, it's a question, and no constraint enforces a guess at
the answer.

## Elicitation checklist

- Mark nouns (entities), verbs (relationships) and "each … has exactly one …" sentences (FDs).
- Merge synonyms; don't model the system itself.
- Ask the **"always?"** question of every fact ("does an order always ship to the customer's
  address?") and walk the rare paths — backorders, transfers, cancellations, corrections — that a first
  model misses.
- Ask which values are recorded **at the time of an event** (price charged, rate applied) and must not
  follow later changes.
- Ask about history (er-modeling §A2.6): audit trail, valid-time history, retention window, current
  state only.
- Ask which invariants must hold **under concurrent use** (stock, quotas, bookings, balances) — they
  decide tier 4 vs tier 2 enforcement.
- Record the source of every element; different departments know different halves of a process.
- Confirm the dossier with the domain owner before modelling; what can't be confirmed stays an open
  question, not an assumption turned into a constraint.
