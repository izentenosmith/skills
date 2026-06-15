---
name: product-requirement-document
description: Turn the current conversation context into a PRD and publish it to the project issue tracker. Use when the user wants to create a PRD from the current context. Best run after the architect-deep-dive skill, which surfaces the design decisions this PRD records.
---

This skill takes the current conversation context and codebase understanding and produces a PRD. Do NOT interview the user — just synthesize what you already know.

## When to run

This works best **immediately after [architect-deep-dive](architect-deep-dive.md)**: that skill resolves the design tree one decision at a time, so by the time you reach this skill the trade-offs, interfaces, and seams are already settled and this becomes pure synthesis. It does NOT require the deep dive first — you can run it any time there's enough context — but if the conversation lacks resolved design decisions, prefer running the deep dive first for stronger results.

The issue tracker and triage label vocabulary should have been provided to you. If they haven't, ask the user which tracker to publish to (e.g. GitHub Issues, Linear, Jira) and what label marks an issue as ready to pick up.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the PRD, and respect any ADRs in the area you're touching.

2. Sketch out the seams at which you're going to test the feature. Existing seams should be preferred to new ones. Use the highest seam possible. If new seams are needed, propose them at the highest point you can.

   Check with the user that these seams match their expectations.

3. Write the PRD using the template below, then publish it to the project issue tracker. Apply the `ready-for-agent` triage label — no need for additional triage.

   When the issue moves to `ready-for-agent`, the authoritative spec an AFK agent works from is the **agent brief** posted as a comment — not the PRD body. After publishing, write that brief following [agent-brief](agent-brief.md).

<prd-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this PRD.

## Further Notes

Any further notes about the feature.

</prd-template>
