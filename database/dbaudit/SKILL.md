---
name: dbaudit
description: Audit a relational database from its DDL — tables, indexes, views, stored procedures, triggers — against relational theory, ER-modelling rules and a scored rubric. Produces per-file findings with severity, confidence and line evidence, a repeatable 0–10 score, per-database summaries and an estate-wide synthesis. Use when grading a legacy schema or DDL dump, assessing database quality or risk, or before planning a database migration or redesign. It evaluates only; dbpropose turns its results into changes.
---

# 🔎 dbaudit

## Where this fits

Two database skills, in order:

1. **dbaudit** (this skill) — grade the DDL: findings, scores, summaries, synthesis
2. [dbpropose](../dbpropose/SKILL.md) — turn those results into verdicts and a target design or
   remediation plan

This skill **evaluates and stops**. It does not recommend a redesign, write target DDL or decide what
to drop — an audit that also prescribes has an incentive to shape its findings toward the prescription.
Evidence, theory and a number; the decisions belong to the next skill.

Scope is **static DDL text**. Anything that needs a live instance — row counts, real index usage,
execution plans, fragmentation, whether a schema is still used — is a 🔬 *needs-data* flag and never
graded as fact.

Reference docs, all in this folder:

- [theory.md](theory.md) — the principles every finding must cite: integrity, functional dependencies,
  normal forms, ACID, SSOT, ER-modelling vocabulary, literature
- [scoring.md](scoring.md) — severity taxonomy, confidence tags, the 0–10 formula, triage, output
  templates
- [audit-lenses.md](audit-lenses.md) — cross-cutting lenses: dead/copy schemas, cross-database coupling,
  dark data, logic drift, security
- [tables.md](tables.md) · [indexes.md](indexes.md) · [views.md](views.md) ·
  [procedures.md](procedures.md) · [triggers.md](triggers.md) — the per-object-type rubrics: 🟢 well
  done, 🔴 anti-patterns, checklist
- [detection-signals.md](detection-signals.md) — the grep/regex behind every anti-pattern, with its
  confidence tag and engine notes
- [er-modeling.md](er-modeling.md) — CAP1–CAP4: the modelling rules the table rubric reads the schema
  against, the reverse-engineering procedure (§A0) and the drills whose legacy symptoms are findings

---

## 📐 Calibrate the pass

Pick one up front and say which:

| Mode | Input | Run |
|---|---|---|
| **File audit** | One DDL file | Steps 0–2 for that file |
| **Database audit** | One database's DDL | Steps 0–3 (per-database summary) |
| **Estate audit** | Several databases | Steps 0–4 (adds the synthesis) |
| **Model audit** | An ER model or schema proposal, no DDL dumps | Grade it against [er-modeling.md](er-modeling.md) — its checklists and the CAP4 drills — and report gaps with severity; skip the scoring formula, which is built for DDL files |

Also state the **source engine**, inferred from the syntax (`IDENTITY`/`dbo`/`INSERTED` → SQL Server;
`:NEW`/`VARCHAR2` → Oracle; `AUTO_INCREMENT` → MySQL). The signals are written for T-SQL;
[detection-signals.md](detection-signals.md) says how each translates.

---

## 🧭 Step 0: Inventory

- [ ] **Locate the DDL** — dumps per object type (`tables.sql`, `procedures.sql`, …), a migrations
  folder, or an export the user produced. If none exists, ask for one; don't connect to a live server to
  make one unless the user says so, and then read-only.
- [ ] **Count objects** per type per database (`CREATE TABLE`, `CREATE … INDEX`, `CREATE VIEW`,
  `CREATE PROC`/`FUNCTION`, `CREATE TRIGGER`). The counts weight the scores later.
- [ ] **Usage status** per database — used / barely used / unused. Not in the DDL: ask, or mark 🔬.
  A **copy database** (one schema duplicating another) *is* decidable — compare object lists — and is
  an SSOT finding on its own.
- [ ] **Source version** — the commit or dump date every evaluation will cite.
- [ ] **Output location** — the repo's convention if it has one; otherwise `<db>/analysis/<type>.md`
  per file, `<db>/analysis/summary.md` per database, and `estate-analysis.md` at the dump root. Results
  never go inside this skill's folder.

## 🔬 Step 1: Evaluate each DDL file

One file, one rubric, one evaluation file. For each:

- [ ] **Triage if large** (≳ 50 objects or 5k lines): signal-scan the whole file with
  [detection-signals.md](detection-signals.md), rank objects by signal density, deep-read the worst
  (≥ 10 % or 20, whichever is larger) plus ~10 at random. **State coverage** — "deep-read 32 of 463;
  signals cover all 463." Smaller files are read in full.
- [ ] **Walk the rubric's 🔴 anti-patterns** against every object.
- [ ] **Every finding carries five things**: object, anti-pattern, **confidence** (✅ decidable /
  ⚠️ proxy / 🔬 needs-data), **the theory it violates** (a named principle from [theory.md](theory.md)),
  **severity** (Critical / High / Medium / Low per [scoring.md](scoring.md)), and **evidence** as a
  file:line reference. A finding missing any of them is incomplete — the theory most of all: a defect
  without the principle it breaks is taste.
- [ ] **Reverse-engineer the model while reading tables** ([er-modeling.md](er-modeling.md) §A0):
  phrase each FK as a two-way relationship sentence, test each PK against the UID criteria (including
  intelligent keys), and look for what was never modelled — repeating groups, unresolved M:M, arcs and
  subtypes hiding in type columns, stored derived totals, history overwritten in place. Record the
  recovered model in the evaluation's notes; dbpropose starts from it.
- [ ] **Cross-file criteria** need both inputs open: FK columns vs. index keys; collation across
  catalogs; a trigger's writes vs. the tables that have triggers. Record them in the file where the
  defect lives.

Write `<db>/analysis/<type>.md` from the template in [scoring.md](scoring.md).

## 🧮 Step 2: Score

Apply the formula in [scoring.md](scoring.md) — proportional grading per criterion, checklist base,
severity caps (any open Critical → 2.0; any open High → 6.0), confidence rule (🔬 never moves a score;
⚠️ alone never grades 🔴). **Show the arithmetic**: `p` per criterion, base, cap and the finding that
set it. Two auditors with the same findings must land on the same number.

## 📋 Step 3: Summarize each database

`<db>/analysis/summary.md`: object counts, per-file scores and the weighted DB score, severity tally,
**🔬 flag tally** (a high score riding on many flags is not a clean bill of health), top findings,
systemic issues, one-paragraph grade. Only after every per-file evaluation for that database exists.

## 🗺️ Step 4: Synthesize the estate

With more than one database, `estate-analysis.md`: capped and un-capped estate scores, the severity
heatmap (database × object type), the findings that only appear across catalogs — collation split,
**cross-database coupling as an edge list (source → target, count)**, dead and copy schemas, RBAR
prevalence, missing-FK-index pattern, error-handling absence — worst offenders, the 🔬 tally, and
prioritized themes each tied to its theory. The coupling edge list is what dbpropose derives its
topology from; give it counts, not adjectives.

---

## 🛑 Stopping rule

Stop when all hold:

- [ ] Every DDL file in scope has an evaluation with its **coverage stated**.
- [ ] Every finding has confidence, theory, severity and a line reference.
- [ ] Every score shows `p`, base and cap, and follows the formula.
- [ ] Every 🔬 flag is listed by name — none silently dropped, none scored.
- [ ] Summaries and the synthesis exist for the mode chosen.

Then stop. **More findings in a file that is already capped by a Critical don't change its number or
its fate** — past full coverage of the checklist, an extra Low is noise that buries the Critical. And
don't start proposing: hand off.

---

## Subagents — optional

Worth it on an estate; rarely on one database.

**Fan out Step 1** — one read-only delegate per database (or per object-type file when a single file is
huge), dispatched together and collected before Step 2. Keep **scoring and the synthesis** in the main
thread: the formula only produces comparable numbers when one auditor applies it, and coupling only
shows when every database is seen at once.

**Dispatch contract.** A delegate starts with no history. Give it the **prior** (what the estate is,
which databases are dead or copies), the **target** (exactly which files it owns, and that the others
are covered), the **context it cannot infer** — paste the relevant rubric doc and its signal table
inline rather than pointing at paths, plus the source engine, the rubric version, and the severity and
confidence definitions — the **return shape** (the findings table from [scoring.md](scoring.md), signal
counts per anti-pattern, coverage, 🔬 flags, recovered-model notes for tables, and "not evaluated" per
file so a silent delegate is distinguishable from a clean one), and an explicit *"report conclusions,
not file excerpts."* Delegates **never score** and **never write** outside their own evaluation files.

---

## Rules of Engagement

1. **Static scope, honestly labelled.** A runtime claim is a 🔬 flag, never a defect.
2. **No finding without its theory.** Name the principle — entity integrity, 3NF, ACID isolation,
   SSOT, the UID invariance rule — or drop the finding.
3. **Evidence is a line reference.** "Several procedures use cursors" is a count; a finding names the
   object and the line.
4. **Score by formula, not by feel.** Show the arithmetic.
5. **Evaluate, don't prescribe.** A fix hint in a finding is fine ("set-based rewrite over the
   pseudo-tables"); a redesign is dbpropose's job.
6. **Read-only.** Never alter a database, a dump or a live instance.
7. **Record the rubric version** (`v1.1`) and the source version in every output.

## Handoff

> Audited `<N>` objects across `<D>` databases (rubric v1.1, source `<commit/date>`). Estate score
> `<x.x>` — `<band>`, capped by `<finding>`. `<c>` Critical · `<h>` High · `<m>` Medium · `<l>` Low;
> `<k>` 🔬 flags open. Outputs: `<paths>`.

Run **[dbpropose](../dbpropose/SKILL.md)** next to turn this into verdicts and a target schema or a
remediation plan. State the score, the capping finding and the open-flag count out loud — they are
what the next stage needs to trust the audit, or not.
