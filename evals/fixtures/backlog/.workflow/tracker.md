# Tracker profile
- **Verified:** 2026-11-02 by reading `.workflow/backlog.md`
- **Tool:** local
- **Location:** `.workflow/backlog.md`
- **Access:** the file itself, committed with the code
- **Language:** English
- **Description format:** Markdown

## Kinds → types
| Kind | Type | Notes |
|---|---|---|
| story | `Kind: story` | |
| bug | `Kind: bug` | |
| spike | `Kind: spike` | |
| task | `Kind: task` | |
| incident | `Kind: bug` + label `prod-incident` | |
| follow-up | `Kind: task` + label `follow-up` and one `action:` label | |
| container | `Kind: epic` | |

## States
| Type(s) | Flow | Done state | Initial state for create |
|---|---|---|---|
| all | todo → doing → review → done (or canceled) | done | todo |

State categories: `todo` is to do; `doing` and `review` are in progress; `done` and `canceled` are done.

## Fields
| Field | Required? | Allowed values / source | Notes |
|---|---|---|---|
| Priority | yes | P1 (highest) · P2 · P3 · P4 | set by whoever files the item; epics have none |
| Parent | no | an epic's id, or none | |
| Due | follow-ups and dated work | a date | |
| Size | not tracked | | |
| Owner | no | ana · bruno · chen · dara | four engineers; no WIP limits set |

## Labels
| Canonical | This team's label |
|---|---|
| prod-incident | `prod-incident` |
| follow-up | `follow-up`, with `action:prevent`, `action:mitigate` or `action:process` |
| unplanned | `unplanned` |
| toil | `toil` |
