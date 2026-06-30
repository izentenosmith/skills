---
name: agent-brief
description: Write the authoritative agent brief comment posted on a GitHub issue when it moves to ready-for-agent. Use when an issue needs a durable, behavioral spec for an AFK agent to work from — typically right after publishing a PRD with the product-requirement-document skill.
---

# Writing Agent Briefs

An agent brief is a structured comment posted on a GitHub issue when it moves to `ready-for-agent`. It is the authoritative specification that an AFK agent will work from. The original issue body and discussion are context — the agent brief is the contract.

This skill is **stage 3 of a four-stage workflow**:

1. [architect-deep-dive](../architect-deep-dive/SKILL.md) — resolves the design tree, scope, and edge cases
2. [product-requirement-document](../product-requirement-document/SKILL.md) — synthesizes those decisions into a PRD
3. **agent-brief** (this skill) — writes the authoritative behavioral spec on the issue
4. [tdd](../tdd/SKILL.md) — builds it red-green-refactor

**Upstream (from the PRD):** the PRD records the decisions for humans; this brief is the durable spec the agent executes against. Pull directly from the PRD — its **Implementation Decisions** become your **Key interfaces**, its **Testing Decisions** become your **Test seams & prior art**, its user stories and resolved edge cases become your **Acceptance criteria**, and its **Out of Scope** becomes your **Out of scope**.

**Downstream (into TDD):** the agent that picks this up will run the [tdd](../tdd/SKILL.md) skill, whose planning step needs four things before it can write a single test — the public interface/seams, a *prioritized* list of behaviors to test, what is explicitly *not* tested, and prior art for similar tests. Shape this brief so all four fall out of it directly. See **Tangling to TDD** below.

## Principles

### Durability over precision

The issue may sit in `ready-for-agent` for days or weeks. The codebase will change in the meantime. Write the brief so it stays useful even as files are renamed, moved, or refactored.

- **Do** describe interfaces, types, and behavioral contracts
- **Do** name specific types, function signatures, or config shapes that the agent should look for or modify
- **Don't** reference file paths — they go stale
- **Don't** reference line numbers
- **Don't** assume the current implementation structure will remain the same

### Behavioral, not procedural

Describe **what** the system should do, not **how** to implement it. The agent will explore the codebase fresh and make its own implementation decisions.

- **Good:** "The `SkillConfig` type should accept an optional `schedule` field of type `CronExpression`"
- **Bad:** "Open src/types/skill.ts and add a schedule field on line 42"
- **Good:** "When a user runs `/triage` with no arguments, they should see a summary of issues needing attention"
- **Bad:** "Add a switch statement in the main handler function"

### Complete acceptance criteria

The agent needs to know when it's done. Every agent brief must have concrete, testable acceptance criteria. Each criterion should be independently verifiable.

- **Good:** "Running `gh issue list --label needs-triage` returns issues that have been through initial classification"
- **Bad:** "Triage should work correctly"

### Explicit scope boundaries

State what is out of scope. This prevents the agent from gold-plating or making assumptions about adjacent features.

## Tangling to TDD

The agent that executes this brief runs the [tdd](../tdd/SKILL.md) skill. Its planning step asks: *"What should the public interface look like? Which behaviors are most important to test?"* and then builds vertically — one test, one slice, tracer-bullet first. A brief that ignores this forces the agent to re-derive the plan from scratch. Shape the brief so TDD planning is a lookup, not a re-design:

- **Name seams, not internals.** TDD tests behavior through the *highest public seam* available and prefers existing seams to new ones. In **Key interfaces**, describe the public entry points (endpoints, service methods, component contracts) the agent will test against — not private collaborators. If a new seam is needed, say so and place it as high as possible.
- **Prioritize the acceptance criteria.** TDD does NOT test everything — it focuses on critical paths and complex logic. Order the criteria so the first is the **tracer-bullet candidate**: the single most important end-to-end behavior that proves the path works. Everything after it is one incremental red→green slice. The agent should be able to read the list top-to-bottom as a build order.
- **State criteria as observable behavior.** Each criterion must be verifiable through the public interface and read like a spec sentence — what the behavior/anti-patterns look like is owned by the [tdd](../tdd/SKILL.md) skill; don't restate it, just conform to it.
- **Separate edge-case criteria from happy-path.** Carry the unhappy paths resolved during architect-deep-dive (empty/missing input, boundaries, permission failures, partial failures, legacy-data quirks) into their own clearly-marked criteria so the agent writes the edge-case slices it would otherwise skip.
- **Supply prior art.** TDD's planning step looks for similar tests already in the codebase. Point at the closest existing test suites/patterns so the agent matches conventions instead of inventing them.

## Template

```markdown
## Agent Brief

**Category:** bug / enhancement
**Summary:** one-line description of what needs to happen

**Current behavior:**
Describe what happens now. For bugs, this is the broken behavior.
For enhancements, this is the status quo the feature builds on.

**Desired behavior:**
Describe what should happen after the agent's work is complete.
Be specific about edge cases and error conditions.

**Key interfaces (test seams):**
- `TypeName` — what needs to change and why
- `functionName()` return type — what it currently returns vs what it should return
- Public entry point the behavior is observable through (endpoint / service method / component contract) — the seam tests should target
- Config shape — any new configuration options needed

**Acceptance criteria** (ordered — first is the tracer-bullet candidate, each one a single red→green slice):
- [ ] Tracer bullet: the most important end-to-end behavior that proves the path works
- [ ] Next most important behavior
- [ ] Next most important behavior
- [ ] Edge case: <unhappy path — empty/missing input, boundary, permission failure, partial failure, legacy-data quirk>
- [ ] Edge case: <unhappy path>

**Test seams & prior art:**
- Highest existing seam to test through (prefer existing seams to new ones)
- Closest existing test suite/pattern in the codebase to mirror for conventions

**Out of scope:**
- Thing that should NOT be changed or addressed in this issue
- Adjacent feature that might seem related but is separate
```

## Handoff

After posting the brief, prompt the user:

> The agent brief is posted. The implementing agent should run the **[tdd](../tdd/SKILL.md)** skill next — its acceptance criteria are ordered as a red→green build order, with the first as the tracer bullet.

## Examples

### Good agent brief (bug)

```markdown
## Agent Brief

**Category:** bug
**Summary:** Skill description truncation drops mid-word, producing broken output

**Current behavior:**
When a skill description exceeds 1024 characters, it is truncated at exactly
1024 characters regardless of word boundaries. This produces descriptions
that end mid-word (e.g. "Use when the user wants to confi").

**Desired behavior:**
Truncation should break at the last word boundary before 1024 characters
and append "..." to indicate truncation.

**Key interfaces (test seams):**
- The `SkillMetadata` type's `description` field — no type change needed,
  but the validation/processing logic that populates it needs to respect
  word boundaries
- The function that reads SKILL.md frontmatter and extracts the description
  — the public seam tests should call

**Acceptance criteria** (ordered — first is the tracer-bullet candidate):
- [ ] Tracer bullet: descriptions over 1024 chars are truncated at the last
      word boundary before 1024 chars and end with "..."
- [ ] Descriptions under 1024 chars are unchanged
- [ ] The total length including "..." does not exceed 1024 chars
- [ ] Edge case: a description whose single first "word" already exceeds
      1024 chars still produces valid, length-bounded output

**Test seams & prior art:**
- Test through the frontmatter-extraction function, not the internal
  truncation helper
- Mirror the existing SKILL.md parsing tests for fixture style and conventions

**Out of scope:**
- Changing the 1024 char limit itself
- Multi-line description support
```

### Good agent brief (enhancement)

```markdown
## Agent Brief

**Category:** enhancement
**Summary:** Add `.out-of-scope/` directory support for tracking rejected feature requests

**Current behavior:**
When a feature request is rejected, the issue is closed with a `wontfix` label
and a comment. There is no persistent record of the decision or reasoning.
Future similar requests require the maintainer to recall or search for the
prior discussion.

**Desired behavior:**
Rejected feature requests should be documented in `.out-of-scope/<concept>.md`
files that capture the decision, reasoning, and links to all issues that
requested the feature. When triaging new issues, these files should be
checked for matches.

**Key interfaces (test seams):**
- Markdown file format in `.out-of-scope/` — each file should have a
  `# Concept Name` heading, a `**Decision:**` line, a `**Reason:**` line,
  and a `**Prior requests:**` list with issue links
- The triage workflow entry point — the public seam tests drive — should read
  all `.out-of-scope/*.md` files early and match incoming issues against them
  by concept similarity

**Acceptance criteria** (ordered — first is the tracer-bullet candidate):
- [ ] Tracer bullet: closing a feature as wontfix creates a file in
      `.out-of-scope/` containing the decision, reasoning, and link to the
      closed issue
- [ ] If a matching `.out-of-scope/` file already exists, the new issue is
      appended to its "Prior requests" list rather than creating a duplicate
- [ ] During triage, existing `.out-of-scope/` files are checked and surfaced
      when a new issue matches a prior rejection
- [ ] Edge case: a malformed or partial `.out-of-scope/` file is skipped
      gracefully rather than aborting triage

**Test seams & prior art:**
- Drive tests through the triage workflow entry point, not the file-matching
  helper in isolation
- Mirror the existing triage workflow tests for setup and fixture conventions

**Out of scope:**
- Automated matching (human confirms the match)
- Reopening previously rejected features
- Bug reports (only enhancement rejections go to `.out-of-scope/`)
```

### Bad agent brief

```markdown
## Agent Brief

**Summary:** Fix the triage bug

**What to do:**
The triage thing is broken. Look at the main file and fix it.
The function around line 150 has the issue.

**Files to change:**
- src/triage/handler.ts (line 150)
- src/types.ts (line 42)
```

This is bad because:
- No category
- Vague description ("the triage thing is broken")
- References file paths and line numbers that will go stale
- No acceptance criteria — so nothing for TDD to slice into red→green cycles
- No prioritization or tracer-bullet candidate, so no build order
- No test seams or prior art, forcing the agent to re-design the test plan
- No scope boundaries
- No description of current vs desired behavior