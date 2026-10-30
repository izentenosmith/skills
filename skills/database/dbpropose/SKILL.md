---
name: dbpropose
description: Turn a database audit, a target design and its ER and relational diagrams into a reviewable proposal — a prioritized decision register, a migration sequence whose every step names its validation, rollback and blast radius, and the open questions each decision waits on — written to proposal/proposal.md for acceptance before any DDL. Use when the user wants a recommendation, remediation or migration plan for a database, "what should we do with this schema", or the step between dbdesign/dbdiagram and dbbuild. It never applies changes; dbaudit grades, dbdesign models, dbbuild writes DDL.
---

# dbpropose

Turn evidence and a design into a recommendation a decision-maker can accept and an implementer can follow. It works alone when the user supplies the artifacts, or as the proposal stage of the database workflow harness.

**A proposal is not authorization.** Never apply DDL, run a migration or write to a database here. The output is a document that someone accepts or sends back.

## Inputs

| Input | Used for | When it's missing |
|---|---|---|
| Audit (summary, findings, score) | Every decision on an existing database cites it | Say so; propose only from requirements and design, invent no finding or score |
| `scores.json`, `gate.md` | Score, cap and gate reasons | Harness-only. Read the score, cap and gate from the audit summary instead |
| Design (`design.md`, model) and its version | The target: entities, keys, constraints | Stop short of a migration plan; recommend running dbdesign |
| ER diagram (Barker) and relational diagram | Cross-checked against the design | Note the gap. Required only when the proposal changes the model |
| Requirements, consumers, target engine | Changes the audit didn't cause, breaking-change impact | Carry as open questions |

## Steps

1. **Inventory the sources and their versions.** List each artifact's path and revision or date. Name what is missing and what that rules out.
2. **Check the diagrams against the design.** A diagram drawn from an older revision, or one that disagrees with the design, is a mismatch. Describe it and route it to [dbdiagram](../dbdiagram/SKILL.md) (or [dbdesign](../dbdesign/SKILL.md) when the design is the one that's wrong). Never redraw or repair either here.
3. **Decide a posture per object.** Decide structure, data and logic separately in the band vocabulary (Reuse / Refactor / Rework / Rebuild). Start from the score band and explain any evidence-based override. See [proposal.md](proposal.md).
4. **Build the decision register,** Critical first, then by dependency. Every row cites the audit finding id it answers. A change no finding asked for (a new table from a requirement, a design decision) says **"no audit finding"** and names what drives it. Never invent a finding id.
5. **Find the consumers of every breaking change.** For anything removed, renamed, retyped or newly constrained, name who reads or writes it: the app, reports, add-ons, ETL, views, integrations. A breaking change with a known consumer is planned as **expand → migrate consumers → contract**, and the contract step is gated on that named consumer having moved. An unknown consumer is an open question, not an assumption.
6. **Sequence the migration.** Data work comes before the constraint it unblocks: orphans resolved before the foreign key, duplicates before the unique key, bad values before the check. Containment comes before structure, and parents before children. Write the sequence as the step table in [proposal.md](proposal.md): every step has its pre-check, validation, rollback and blast radius.
7. **Carry the unknowns.** Every unresolved needs-data flag, every unknown consumer and every unconfirmed assumption becomes an open question that names the decision it blocks.
8. **Write `proposal/proposal.md`** (or the path the user names) in the structure in [proposal.md](proposal.md). End it with the acceptance line. Your response summarizes the recommendation and links the file; the proposal itself never lives only in the chat.

## Before you hand off

- [ ] The file exists at its path, and every artifact it relies on is cited by path.
- [ ] Every register row has a finding id from the audit, or says "no audit finding" and why.
- [ ] Every breaking change names its consumers and, where one is known, is expand/contract with a gated contract.
- [ ] No constraint is added before the data step that makes it hold.
- [ ] Every migration step has its validation, rollback and blast radius filled in.
- [ ] Diagram mismatches are described and routed, not fixed.
- [ ] The proposal closes with the acceptance line.

## Handoff

For an existing database the usual sequence is [dbaudit](../dbaudit/SKILL.md) → [dbdesign](../dbdesign/SKILL.md) → [dbdiagram](../dbdiagram/SKILL.md) → this proposal → [dbbuild](../dbbuild/SKILL.md). For a new database, start at dbdesign. Each stage may also run alone when its inputs are available. Close with:

> This proposal needs explicit acceptance before **[dbbuild](../dbbuild/SKILL.md)** generates DDL from it. Changes to its structure go back through dbdesign and dbdiagram, and the revised proposal needs acceptance again.
