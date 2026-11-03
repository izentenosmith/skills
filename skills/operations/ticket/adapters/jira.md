# Adapter — Jira

Jira is reachable three ways. Use the first that the machine already has, in this order:

1. **An Atlassian MCP server** connected to the agent — its tools take care of auth and the description format.
2. **A Jira CLI** that's installed and logged in — Atlassian's `acli` or the community `jira` CLI. Flags differ between them and between versions: check `--help` of the installed one before relying on a flag below.
3. **The REST API**, with credentials from environment variables: Jira Cloud uses basic auth with `JIRA_EMAIL` and an API token in `JIRA_API_TOKEN` against `https://<site>.atlassian.net/rest/api/3/`; Jira Data Center uses a personal access token as a bearer token against `/rest/api/2/`.

Placeholders: `<site>`, `<KEY>` (project key), `<KEY-123>` (issue key).

## Canonical → Jira

| Canonical | Jira |
|---|---|
| kind | Issue type — Story, Bug, Task, Epic, Sub-task, plus custom types; team-managed and company-managed projects differ |
| state | Status. **Statuses are not set; they are reached by a transition**, and the transitions available depend on the current status and the workflow |
| state category | `statusCategory`: To Do · In Progress · Done |
| container | Sprint — a custom field whose id varies per site (`customfield_NNNNN`), set to the sprint's numeric id |
| area | Component, or the project itself, or a custom field — whatever recent issues use |
| label | `labels` — strings with **no spaces** |
| description format | Cloud v3: **Atlassian Document Format** (JSON). v2 and Data Center: wiki markup. Most CLIs and MCP tools accept Markdown and convert it |
| hours | Time tracking: worklogs (`timeSpentSeconds`) and `timetracking.originalEstimate` — only if time tracking is enabled. Story points: a custom field ("Story point estimate" in team-managed, "Story Points" in company-managed) |
| assignee | Cloud: an `accountId`, not an email — look it up with `GET /rest/api/3/user/search?query=<email>` |

## Preflight

```bash
curl -sf -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "https://<site>.atlassian.net/rest/api/3/myself" | head -c 200
```

A 401 means the token is wrong or revoked: the user creates a new API token in their Atlassian account and sets it themselves.

## Discovering the schema

```bash
# Issue types available in the project, then the fields of one type — required flags and allowed values
GET /rest/api/3/issue/createmeta/<KEY>/issuetypes
GET /rest/api/3/issue/createmeta/<KEY>/issuetypes/<issueTypeId>
# Every field's id and name — find the Sprint and story-point custom field ids here
GET /rest/api/3/field
# Statuses per issue type in the project
GET /rest/api/3/project/<KEY>/statuses
```

**The current sprint:** `GET /rest/agile/1.0/board/<boardId>/sprint?state=active` (find the board with `GET /rest/agile/1.0/board?projectKeyOrId=<KEY>`), or select by JQL with `sprint in openSprints()`.

## Searching (reconcile)

JQL, through the CLI, the MCP server, or `GET /rest/api/3/search/jql?jql=…&fields=summary,status,labels,assignee` (the older `/rest/api/3/search` endpoint is deprecated on Cloud; page with `nextPageToken`).

```
project = <KEY> AND sprint in openSprints() AND assignee = currentUser()
project = <KEY> AND text ~ "invoice total" AND statusCategory != Done
project = <KEY> AND labels = prod-incident ORDER BY created DESC
project = <KEY> AND statusCategory != Done AND updated <= -30d
```

## Create

```bash
POST /rest/api/3/issue
{"fields": {
  "project": {"key": "<KEY>"},
  "issuetype": {"name": "<Type>"},
  "summary": "<title>",
  "description": {"type": "doc", "version": 1, "content": [
    {"type": "paragraph", "content": [{"type": "text", "text": "<text>"}]}]},
  "labels": ["prod-incident"],
  "assignee": {"accountId": "<accountId>"},
  "parent": {"key": "<KEY-1>"},
  "customfield_<sprint>": <sprintId>
}}
```

A create rejected with `Field '<x>' is required` names a field the profile must add; `Field '<x>' cannot be set` means it isn't on the create screen for that type.

## Transition and close

```bash
GET  /rest/api/3/issue/<KEY-123>/transitions                       # what's reachable from here
POST /rest/api/3/issue/<KEY-123>/transitions
{"transition": {"id": "<id>"},
 "fields": {"resolution": {"name": "Done"}},
 "update": {"comment": [{"add": {"body": <ADF comment>}}]}}
```

- The transition **id** is per workflow — look it up every time; never reuse one from another project.
- **Set a resolution when the done transition's screen has one.** An issue in a Done status with no resolution still counts as "Unresolved" in filters and reports, and its resolution date stays empty.
- Reaching a status two steps away takes two transitions.

## Labels — set versus add

- `PUT /rest/api/3/issue/<KEY-123>` with `"fields": {"labels": [...]}` **replaces** the whole set.
- `"update": {"labels": [{"add": "prod-incident"}, {"remove": "prod_incident"}]}` adds and removes individually — use this form so existing labels survive.

## Hours

```bash
POST /rest/api/3/issue/<KEY-123>/worklog
{"timeSpentSeconds": 5400, "comment": <ADF comment>}
```

Only after the user confirms the number ([traceability.md](../traceability.md)).

## Linking

- **Commits and PRs:** with a code-host integration installed (GitHub for Jira, Bitbucket, GitLab), the issue key in a branch name, commit message or PR title links it in the development panel. With smart commits enabled, `<KEY-123> #comment <text> #time 1h 30m` also comments and logs time — confirm smart commits are on before relying on them.
- **Without an integration:** `POST /rest/api/3/issue/<KEY-123>/remotelink` with `{"object": {"url": "<commit or PR url>", "title": "<sha> <subject>"}}`.
- **Between issues:** `POST /rest/api/3/issueLink` with `{"type": {"name": "Relates"}, "inwardIssue": {"key": …}, "outwardIssue": {"key": …}}` — also `Duplicate`, `Blocks`, `Cloners`. List the site's link types with `GET /rest/api/3/issueLinkType`.

## Read back

```
key in (<KEY-1>, <KEY-2>)
```

with `fields=status,resolution,labels,assignee,customfield_<sprint>,<required custom fields>`, and check every row.

## Dates for metrics

`created`, `resolutiondate` (only when a resolution is set) and `statuscategorychangedate`. For restore time, prefer the incident label plus `resolutiondate`, and check how many closed incidents actually have one.

## Errors and their causes

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Token wrong, revoked or for another site | The user issues a new API token |
| `Field '<x>' is required` | Required by the create screen or a validator | Add it to the profile |
| `Field '<x>' cannot be set. It is not on the appropriate screen` | Not on that type's create or edit screen | Set it in a later edit, or ask an admin |
| `Transition id '<n>' is not valid for this issue` | Wrong workflow, or not reachable from the current status | Re-read the available transitions |
| `The label '<x>' contains spaces` | Labels can't contain spaces | Use hyphens |
| `Specify a valid 'id' or 'name' for Assignee` | Email used instead of `accountId` on Cloud | Look up the account id |
| Description shows raw JSON or markup | Wrong format for the API version | ADF on v3, wiki markup on v2 |
