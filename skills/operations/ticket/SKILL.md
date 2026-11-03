---
name: ticket
description: Create, update, close and log time on work items in Linear, Azure DevOps or Jira — or in a local markdown log when there is no tracker — without hardcoding anything about the team. Discovers the tracker, its item types, states, required fields, sprints or cycles and label conventions at runtime and caches them in a project profile; reconciles against existing items before creating any; writes descriptions a reader can act on; links commits and PRs; reads every write back. Use when the user asks to create, file, raise, update, move, close or document a ticket, issue, bug, story, task or work item; to turn a list of bugs or commits into tickets; to log hours; to open an incident item or post-mortem follow-ups; or to tag a production failure for DORA metrics. Not for shaping, splitting or ordering a whole backlog — that is backlog.
---

# 🎫 Ticket

## Where this fits

Every other skill in this repo eventually owes the tracker something: hotfix owes a follow-up for its band-aid, incident-fix owes an incident item and its follow-ups, post-mortem's factors become owned work, and [backlog](../backlog/SKILL.md) proposes splits and closures. This skill is the one place that writes to the tracker, so the rules live once: **discover, don't guess · reconcile before creating · confirm before writing · read back after writing.**

It is tool-agnostic by construction. The workflow below speaks in **canonical terms** — *kind*, *state category*, *container*, *area*, *label* — and an adapter translates them for the tool the project uses:

- [adapters/azure-devops.md](adapters/azure-devops.md) — `az boards`, WIQL, and `az rest` for what the CLI can't do
- [adapters/jira.md](adapters/jira.md) — a Jira CLI, an Atlassian MCP server, or REST with JQL; transitions instead of states
- [adapters/linear.md](adapters/linear.md) — the Linear MCP server or the GraphQL API
- [adapters/local.md](adapters/local.md) — a markdown log in the repo when there is no tracker

And four reference docs:

- [profile.md](profile.md) — the `.workflow/tracker.md` project profile: what it caches and how each value is found
- [writing.md](writing.md) — titles and descriptions per kind: story, bug, spike, task, incident, follow-up
- [labels.md](labels.md) — the canonical label set: production incidents for DORA, causes, action types, toil, unplanned work
- [traceability.md](traceability.md) — commits and PRs on the item, closing comments, and hours that are never invented

**Never create, update, transition or close an item without the user's confirmation** of the exact change set. A confirmation covers the items it listed, not the next batch. Credentials never pass through the chat or land in a file: when auth fails, the user re-authenticates themselves.

## 🔎 Step 0: Load or build the profile

Read [profile.md](profile.md). If `.workflow/tracker.md` exists and was verified recently, it *is* step 0 — confirm it in one line. Otherwise build it:

- **Which tracker**, from evidence only: the git remote, ticket keys in commit messages and branch names, tracker links in docs and PR templates, connected MCP servers, installed and authenticated CLIs. Two candidates, or none: ask. No tracker at all: use [adapters/local.md](adapters/local.md) — never invent one.
- **The live schema** from the tracker's own API, never from memory or a template: item types, states per type, required fields and their allowed values, the current sprint or cycle, areas or components, labels in use, the estimate or hours field, and the language items are written in.
- **The team's conventions** from history: which types the team actually uses (a process template exposes more than a team uses), how titles read, which labels mark incidents.

Ask what can't be discovered **once, in a single question**, and save the answers to the profile.

## 🔐 Step 1: Preflight

- [ ] **Auth works** — run the adapter's read-only probe. Expired or missing credentials: stop and give the user the login command to run themselves.
- [ ] **Volatile values are re-resolved, not reused** — the current sprint or cycle, and any allowed value you're about to write. Naming conventions drift (a sprint path that gained or lost a separator, a renamed state); a cached value that fails is re-queried, not retried.

## 🧮 Step 2: Reconcile — the most important step

**Never create before searching.** Work often already has an item — sometimes still open although it shipped, sometimes filed by someone else under a different title. Query the current container (and the assignee, and keywords, and commit SHAs or PR numbers when documenting finished work) using the adapter's search, then classify every candidate:

| Situation | Action |
|---|---|
| An item exists and is done | **Skip.** Report it as an existing duplicate. |
| An item exists and is open | **Update or close that item** with a comment citing the evidence. Don't create a second. |
| An item covers part of it | Create a **continuation** that links the original. |
| Nothing exists | Create. |
| Two existing items describe the same work | Propose linking one as a duplicate of the other; don't silently pick one. |

Present the classified table to the user **before writing anything**.

## ✍️ Step 3: Draft

For each item to create or change:

- [ ] **Kind** — story, bug, spike, task, incident or follow-up ([writing.md](writing.md)) — mapped to the tool's type through the profile. If the kind isn't evident, ask.
- [ ] **Title and description** from [writing.md](writing.md)'s template for that kind, in the profile's language and the tool's description format (HTML, Markdown, or Atlassian Document Format — the adapter says which).
- [ ] **Every required field** from the profile, plus the fields the team always fills even where no rule enforces them — a missing area or component is a silent data-quality bug.
- [ ] **Labels** from [labels.md](labels.md): a production failure always carries the incident label, opened when the failure starts, not after it's fixed.
- [ ] **Traceability** from [traceability.md](traceability.md): commits, PRs and scope for finished work; the item it continues or duplicates.
- [ ] **Hours or estimate**, if the team tracks them: proposed from evidence, **labelled as an estimate**, and confirmed — never filled in silently.

## ✅ Step 4: Confirm, then write

Show the change set as a table — per item: action (create / update / transition / close / comment), type, title, the fields that change, and labels added. Wait for confirmation.

Then write through the adapter, **one item at a time, reporting OK or FAIL per item** without aborting the batch on a single failure. Items created to document finished work start in the initial state and are then transitioned — most trackers refuse an arbitrary initial state. Closing always adds a comment that cites the evidence.

## 🔁 Step 5: Read back — mandatory

Never declare an item written until a fresh query shows it. Re-read every item touched, in one query where the tool allows it, and check each row: the state is the target, every required and always-filled field is set, labels are present (and **no stray label was appended** — some tools add rather than replace), hours or estimate set where closing requires them, links present. A mismatch is fixed and re-read, not reported as done.

## 🛑 Stopping rule

- **Auth fails** and the user isn't there to re-authenticate → stop with the drafted change set saved to `.workflow/ticket-pending.md`, so nothing is lost.
- **A required field has no discoverable value** and the user hasn't answered → stop; don't pick a plausible value.
- **Reconciliation is ambiguous** — a candidate might be the same work or might not → ask; a duplicate costs more to clean up than a question.

Otherwise, stop when every item is read back and reported.

## Subagents — optional

**Reconciliation searches delegate well** when documenting a long commit range: one read-only delegate per area or per week, each returning candidate items with ids and states. Drafting, confirmation and every write stay in the main thread. **Dispatch contract:** the prior, the target, the context it cannot infer, the return shape, and *"report conclusions, not raw query output."*

## Handoff

> Tracker `<tool / project>`: created `<ids>`, updated `<ids>`, closed `<ids>`; skipped as existing `<ids>`. Read back: all fields verified `<or: what was fixed>`. Estimates confirmed by the user: `<ids>`. `<failures, or "no failures">`.
