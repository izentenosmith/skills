# Records — the ADRs and glossary entries a design leaves behind

A resolved decision that lives only in the session is re-argued the first time someone finds it inconvenient. The brief carries decisions into one build; these two files carry them into every build after it. Write them **as decisions resolve**, not in a batch at handoff, so a session that ends early still leaves its record.

## Where they go

Use what the repo already has. Look before creating anything:

- **ADRs** — an existing decisions folder (`docs/adr/`, `doc/adr/`, `adr/`, `docs/decisions/`, or whatever the repo's agent instructions name). Match its numbering, file naming and template; the format below is only for a repo that has none.
- **Glossary** — an existing `GLOSSARY.md`, `CONTEXT.md`, `docs/glossary.md`, or the glossary the instructions point at. If the repo keeps one per area, write to the one for the area you're touching.

**Create lazily.** No folder and no glossary yet: create `docs/adr/` with the first ADR worth writing, and `GLOSSARY.md` at the root with the first term worth defining — never empty placeholders.

## When a decision earns an ADR

Write one only when **all three** hold:

1. **Hard to reverse** — its row in the options table says *expensive* to reverse (a data migration, a public contract, a boundary other code will grow around).
2. **Surprising without context** — a reader six months on would ask "why did they do it this way?"
3. **A real trade-off** — there were live alternatives, and one was picked for stated reasons.

If any is missing, skip it. Do **not** write one for:

- an **[inferred]** answer that an existing ADR already settled — cite that ADR instead;
- a **deferred** decision — nothing was decided; it goes to the brief's **Deferred by design**;
- a choice the codebase forced with no alternative — that is a fact, not a decision.

**Contradicting an existing ADR** is its own decision (see *First action*). When the user takes the new branch, write the new ADR, mark it as superseding the old one, and change only the old one's status line to `Superseded by <new id>`.

## ADR format (when the repo has none)

`docs/adr/NNNN-<kebab-title>.md`, numbered from `0001`, one decision per file:

```markdown
# NNNN. <Decision, stated as what was chosen — "Cutoff window is configured per account">

**Status:** Accepted · <date> · from the design review of <charter title>

## Context
The forces in one paragraph: the problem from the charter, and the constraint that made this a real choice.

## Decision
What was chosen, in the project's glossary vocabulary.

## Options considered
- **<Chosen>** — buys <…>; costs <…>; reversal: expensive — <why>
- **<Rejected>** — buys <…>; costs <…>; rejected because <…>

## Consequences
What this makes easy, what it makes hard, and **what would change our mind** — carried from the recommendation, so a later reader knows which fact reopens it.
```

The options and the *what would change my mind* line come straight from the question's options table and recommendation. Copy them; don't re-derive them.

## Glossary entries

Add an entry when a question settles **what a word means**: the user's word and the code's word turn out to differ, one term is doing two jobs ("account" meaning both Customer and Login), or a new concept gets named.

```markdown
**<Term>** — <what it is, in one or two sentences of domain language>. _Avoid:_ <the synonyms and overloaded words it replaces>.
```

The glossary defines the domain, nothing else: no file paths, no implementation, no decisions — those belong in ADRs and the brief. Reuse the vocabulary in every question that follows, and flag it when the user later uses a term against its definition.

## Telling the user

Writing a record is part of resolving the question, so say it in one line at the head of the next question, under the progress line:

```
Recorded: docs/adr/0003-cutoff-window-per-account.md · GLOSSARY.md: Cutoff window
```

The user can veto either; a vetoed ADR is deleted, not kept as a draft.
