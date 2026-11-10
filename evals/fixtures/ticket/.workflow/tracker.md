# Tracker profile
- **Verified:** 2026-10-08 by `curl -sf -H "Authorization: Bearer $JIRA_PAT" https://jira.fernhill.example/rest/api/2/myself`
- **Tool:** jira (Data Center 9.12)
- **Location:** https://jira.fernhill.example, project key FH, board "FH Scrum" (id 14)
- **Access:** REST v2, personal access token in env var `JIRA_PAT`, set by each person in their own shell — never the token itself
- **Language:** English
- **Description format:** Jira wiki markup (REST v2)

## Kinds → types
| Kind | Type | Notes |
|---|---|---|
| story | Story | |
| bug | Bug | |
| spike | Spike | time box in Original Estimate |
| task | Task | |
| incident | Bug + label `incident:prod` | |
| follow-up | Task + label `follow-up` | |
| Do not use | Improvement, New Feature, Epic for single items | template leftovers, unused since 2024 |

## States
| Type(s) | Flow | Done state | Initial state for create |
|---|---|---|---|
| Story, Task, Bug, Spike | To Do → In Progress → In Review → Done | Done (resolution Done) | To Do |

## Fields
| Field | Required? | Allowed values / source | Notes |
|---|---|---|---|
| Sprint (`customfield_10104`) | convention: bugs and incidents go into the current sprint; stories, tasks and spikes go to the backlog (no sprint) until refinement | current: **FH Sprint 44** (id 412) | sprint id, not name, in the API |
| Component | convention (98% of items) | Booking · Patient app · Front desk · Payments · Notifications · Reporting | Booking = slots, calendar, availability; Patient app = the patient web and mobile UI; Front desk = receptionist screens; Payments = charges, refunds, receipts; Notifications = SMS, email, push; Reporting = exports and dashboards |
| Clinic impact (`customfield_10231`) | required on Bug | None · One clinic · Several clinics · All clinics | create fails without it; None for anything not in production |
| Incident severity (`customfield_10240`) | required on any item labelled `incident:prod` | SEV-1 · SEV-2 · SEV-3 · SEV-4 | set by the incident commander from the on-call severity matrix (Confluence: OPS/Severity) |
| Story Points | at refinement, not at create | Fibonacci | estimate, confirmed by the team |
| Hours | not tracked | | |

## Labels
| Canonical | This team's label |
|---|---|
| prod-incident | `incident:prod` |
| caused-by-<deploy-id> | `caused-by:<release>`, e.g. `caused-by:4.11.2` |
| follow-up | `follow-up`, with one of `action:mitigate` · `action:prevent` · `action:process` |
| unplanned | `unplanned` |

## Linking
- **Commits:** GitHub for Jira is installed; the issue key in a branch name or commit message links it.
- **Issue links:** Relates · Duplicate · Blocks · Cloners
- **Assignee format:** Jira username (`dmorales`, `ccastro`, `pnavarro`)

## Known traps
- `PUT` with `fields.labels` replaces the whole set; use `update.labels` with `add`.
- Creating a Bug without Clinic impact fails with `Field 'Clinic impact' is required`.
