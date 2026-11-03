# The project profile — `.workflow/tracker.md`

Everything this skill knows about one team's tracker, discovered once and cached in the repo. It is what lets the skill stay generic: the workflow speaks in canonical terms, the profile maps them to this team's reality, and the adapter turns that into commands.

**It holds no secrets** — no tokens, no passwords, no session cookies. Auth lives in the tool's own credential store or an environment variable the user sets.

## Discovery — where each value comes from

| Value | Where to find it | If it can't be found |
|---|---|---|
| **Tool** | Git remote (`dev.azure.com`, `visualstudio.com`), ticket keys in commits and branch names (`AB#123` → Azure Boards; `ABC-123` → Jira or Linear — a `linear.app` link or a branch like `user/abc-123-title` says Linear, an `atlassian.net` link says Jira), PR templates, docs, connected MCP servers, authenticated CLIs | Ask; with no tracker, use the local adapter |
| **Organization / site / workspace, project or team** | CLI defaults (`az devops configure -l`), CLI config files, links in docs | Ask |
| **Item types the team uses** | The tool's type list **intersected with recent history** — a process template exposes types the team never uses | Ask which to use for each kind |
| **States per type** | The tool's workflow for each type, with each state's category (todo / in progress / done / canceled) | — always discoverable |
| **Required fields and allowed values** | The tool's field metadata and validation rules; a rejected test write is also evidence | Ask |
| **Fields always filled though not required** | The fill rate in recent items — a field set on nearly every item is a convention | — |
| **Container** (sprint, iteration, cycle) | The current one from the tool, re-resolved every run | Ask for the number or name |
| **Area** (area path, component, team, module, project) | Field values in recent items, with the domain each covers | Ask when a new item's domain is ambiguous |
| **Labels in use** | Label or tag values in recent items | Use [labels.md](labels.md)'s canonical names |
| **Hours / estimate field** | A numeric field filled on closed items; the team's estimate scale | "not tracked" |
| **Assignee identity format** | The assignee value on the user's own recent items — the sign-in name is not always the email address | Ask |
| **Language of item text** | The language of recent titles and descriptions | Ask |
| **Commit / PR linking** | Existing links on recent items; the integration's mention syntax | "description only" |

**Discover, then verify against history.** Metadata says what the tool allows; history says what the team does. Where the two disagree — a type nobody uses, a field the rules don't require but every item has — the history wins for drafting and the metadata wins for validation.

## Format

```markdown
# Tracker profile
- **Verified:** <UTC date> by <how — the probe command>
- **Tool:** <azure-devops | jira | linear | local>
- **Location:** <organization + project | site + project key | workspace + team key | .workflow/backlog.md>
- **Access:** <CLI and version | MCP server name | REST with env var NAME> — never the credential itself
- **Language:** <language of titles and descriptions>
- **Description format:** <HTML | Markdown | ADF>

## Kinds → types
| Kind | Type | Notes |
|---|---|---|
| story | <type> | <when to use which, if the team splits by frontend/backend/full stack> |
| bug | <type> | |
| spike | <type> | |
| task | <type> | |
| incident | <type> + label `<incident label>` | |
| follow-up | <type> + label `<follow-up label>` | |
| Do not use | <types the template exposes but the team doesn't> | |

## States
| Type(s) | Flow | Done state | Initial state for create |
|---|---|---|---|

## Fields
| Field | Required? | Allowed values / source | Notes |
|---|---|---|---|
| <container> | yes | resolve live: <command> | <format trap, if any> |
| <area / component> | convention | <values, with the domain each covers> | |
| <hours / estimate> | on close | <scale, observed range and median> | estimate, confirmed |
| <custom required field> | yes | <value> | create fails without it |

## Labels
| Canonical | This team's label |
|---|---|
| prod-incident | <…> |
| caused-by-<deploy-id> | <…> |

## Linking
- **Commits:** <mention syntax and/or API link format, repo identifier>
- **Assignee format:** <format>

## Known traps
- <a trap found the hard way, with the error message it produces and the fix>
```

## Keeping it true

- **Re-verify on failure.** A write rejected for an invalid value means the cached value went stale: re-query, update the profile, then retry — once.
- **Record traps as you find them.** Every error that took more than one attempt goes into *Known traps* with its message and fix. That table is where a team's tracker knowledge accumulates instead of being rediscovered each time.
- **Propose, don't apply, schema fixes.** If the picklist is missing a value that a large share of items need (one catch-all value absorbing half the board is the usual sign), say so to the user — changing the tracker's schema is their call.
- **Commit the profile** with the repo's other agent configuration, so the next session and the next person start from it.
