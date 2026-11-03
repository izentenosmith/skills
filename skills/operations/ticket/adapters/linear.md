# Adapter — Linear

Linear is reachable two ways. Use the first the machine already has:

1. **The Linear MCP server** connected to the agent — its tools (list, get, create and update issues; list teams, statuses, labels, cycles; create comments) handle auth.
2. **The GraphQL API** at `https://api.linear.app/graphql`, with a personal API key from an environment variable: header `Authorization: $LINEAR_API_KEY` (a personal key takes no `Bearer` prefix; an OAuth token does).

There is no official Linear CLI; don't install a community one without the user asking.

Placeholders: `<TEAM>` (team key, such as `ENG`), `<TEAM-123>` (issue identifier).

## Canonical → Linear

| Canonical | Linear |
|---|---|
| kind | There are **no issue types**. Kind is carried by a **label** (often in an exclusive label group such as *Type: Bug / Feature / Improvement*) — the profile says which |
| state | Workflow state, per team |
| state category | The state's `type`: `triage` · `backlog` · `unstarted` · `started` · `completed` · `canceled` |
| container | Cycle (per team, optional — `team.activeCycle`); larger groupings are projects |
| area | Team, and project |
| label | Labels, workspace- or team-scoped, optionally grouped |
| description format | Markdown |
| priority | `0` none · `1` urgent · `2` high · `3` medium · `4` low |
| hours | **None** — Linear has estimates (per-team scale: exponential, Fibonacci, linear or t-shirt; may be disabled) but no time tracking and no custom fields |

## Preflight

```graphql
query { viewer { id name email } }
```

An authentication error means the key is wrong or revoked: the user creates a new one in Linear's API settings and sets it themselves.

## Discovering the schema

```graphql
query {
  teams { nodes {
    id key name
    activeCycle { id number }
    states { nodes { id name type position } }
    labels { nodes { id name parent { name } } }
  } }
  issueLabels(filter: { team: { null: true } }) { nodes { id name parent { name } } }
}
```

Mutations take **ids** (`teamId`, `stateId`, `labelIds`), not names — resolve names to ids from this query and cache the mapping in the profile.

## Searching (reconcile)

```graphql
query {
  issues(filter: {
    team: { key: { eq: "<TEAM>" } }
    state: { type: { nin: ["completed", "canceled"] } }
    title: { containsIgnoreCase: "invoice total" }
  }) { nodes { identifier title state { name type } labels { nodes { name } } updatedAt } }
}
```

- Incidents: `labels: { name: { eq: "prod-incident" } }`.
- Stale items: `updatedAt: { lt: "-P30D" }` — date filters accept ISO 8601 durations relative to now.
- Full-text: `searchIssues(term: "…")`.
- `issue(id: "<TEAM-123>")` accepts the human identifier as well as the UUID.

## Create

```graphql
mutation {
  issueCreate(input: {
    teamId: "<team id>"
    title: "<title>"
    description: "<markdown>"
    stateId: "<state id>"
    labelIds: ["<id>", "<id>"]
    assigneeId: "<user id>"
    cycleId: "<cycle id>"
    projectId: "<project id>"
    priority: 2
    parentId: "<parent issue id>"
  }) { success issue { identifier url } }
}
```

Issues created by integrations may land in **Triage**; issues created through the API land in the team's default state unless `stateId` is given.

## Update, transition, close

```graphql
mutation {
  issueUpdate(id: "<TEAM-123>", input: { stateId: "<completed state id>" }) { success }
}
mutation {
  commentCreate(input: { issueId: "<issue id>", body: "Implemented in <shas>; verified in <environment>." }) { success }
}
```

Any state can be set directly — there are no transition rules — so the skill's own checks are the only thing keeping a ticket from jumping to done without evidence.

## Labels — replace versus add

- `labelIds` in `issueUpdate` **replaces** the whole set.
- `addedLabelIds` and `removedLabelIds` change individual labels — use these so existing labels survive.
- A label in an **exclusive group** replaces its sibling (an issue has one *Type*), which is the point; don't fight it.

## Linking

- **Commits and PRs:** with the GitHub or GitLab integration, a branch named from the issue (`issue.branchName`) or the identifier in a PR title or description links them. **Magic words** in a PR description — `Fixes`, `Closes`, `Resolves <TEAM-123>` — also move the issue to done on merge; `Ref` or `Part of <TEAM-123>` links without closing. Confirm with the user before using a closing word: the merge becomes the close.
- **Without an integration:** `attachmentLinkURL(issueId: "<issue id>", url: "<commit or PR url>", title: "<sha> <subject>")`.
- **Between issues:** `issueRelationCreate(input: { issueId, relatedIssueId, type: related })` — also `blocks` and `duplicate`.

## Read back

```graphql
query { issues(filter: { id: { in: ["<id>", "<id>"] } }) {
  nodes { identifier title state { name type } labels { nodes { name } } cycle { number } assignee { name } priority estimate }
} }
```

## Dates for metrics

`createdAt`, `startedAt`, `completedAt` and `canceledAt` are populated automatically by state type, so cycle time and restore time can be read directly — provided the incident issue was created when the failure began.

## Errors and their causes

| Error | Cause | Fix |
|---|---|---|
| `Authentication required` | Missing or revoked key, or `Bearer` added to a personal key | The user sets a valid key; drop `Bearer` for personal keys |
| `Entity not found` | A name passed where an id is expected, or another team's id | Resolve ids from the team query |
| Labels disappeared after an update | `labelIds` replaced the set | Use `addedLabelIds` / `removedLabelIds` |
| Estimate rejected | The value isn't on the team's scale, or estimates are off | Read the team's estimate settings |
| Issue closed on merge unexpectedly | A magic word in the PR description | Use `Ref` / `Part of` unless the merge should close it |
