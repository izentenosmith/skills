# The notes folder

One folder, shared by the nexus and every session it runs, outside every worktree so that it outlives them: `.workflow/nexus/` in the main checkout unless the user names another place. Each brief carries its absolute path.

Who writes what:

| File | Written by | Read by |
|---|---|---|
| `status.md` | the nexus, rewritten every turn | the nexus after compaction; the user |
| `decisions.md` | the nexus, the moment the user decides | every session, before asking anything |
| `findings.md` | the nexus, from what sessions report | every session, at the start of each stage |
| `labels.md` | the nexus, when it hands out an id | every session, before citing a label |
| `resources.md` | the nexus, when it grants or moves a lease or assigns a number | every session, before using a shared resource |
| `owner-checks.md` | the nexus | the user |
| `sessions/<slug>.md` | the session, every turn; the nexus appends `## From nexus` | the nexus |

A session writes only its own log. Everything else it asks the nexus for.

## `status.md` — the whole state

Rewritten, not appended, at the end of every nexus turn. It is what the nexus reads first after a compaction, so it must stand on its own.

```markdown
# Nexus — <increment>
**Updated:** <YYYY-MM-DD HH:MM> · **Base:** <branch> at `<sha>` · **Running:** <n> of <limit> · **Free disk:** <n> GB

| Session | Parent | Slice or track | PR | Stage | Waiting on | Next |
|---|---|---|---|---|---|---|
| <slug> (<id or link>) | — or <owner slug> | <slice or track> | #n at `<sha>` | <stage> | nothing / user: Q-… / nexus / resource: … / run: … / **stalled since <time>** | <one step> |

## Waiting on the user
- Q-<session>-<n> — <question in a line> (since <time>)
- PR #n — ready to merge at `<sha>` (since <time>)

## Leases
- <resource> — <holder> since <time>, limit <time>; queue: <slug>, <slug>

## Archived
- <slug> — PR #n merged at `<sha>`, archived <date>, worktree removed
```

## `decisions.md` — the user's decisions

The register sessions read before asking anything, and the nexus reads before bringing anything to the user. One entry per decision, never edited after the fact — a reversed decision gets a new entry that names the one it supersedes.

```markdown
## DEC-<n>: <the decision, in a line>
**Decided:** <date> by <the user> · **Asked by:** <session or the nexus> · **Applies to:** all sessions | <slugs>
**Question:** <as it was asked>
**Answer:** "<the user's words, verbatim>"
**Means:** <what a session does differently because of it>
**Supersedes:** DEC-<m> | —
```

## `findings.md` — findings that cross slices

A finding goes here when it touches a slice other than the one that found it, or changes a decision.

```markdown
## X-<n>: <the finding in a line>
**Found by:** <session>, <stage>, <date> · **Affects:** <slugs or slices> · **Status:** open | routed | closed
**Evidence:** <counts, query, file:line — what someone else can re-run>
**Routed:** <date> to <sessions> — <what each was asked to do>; to the user as Q-… if it changes a decision
**Closed by:** <PR, sign-off or decision>
```

## `labels.md` — label series

Every series of ids that reports, tickets and sign-offs cite. A session asks for the next id; it never coins a series.

```markdown
| Series | Means | Taken | Next free | Owner |
|---|---|---|---|---|
| <prefix> | <what an id in this series means, e.g. a difference the user signed off, with counts> | <prefix>1–<prefix>n | <prefix>n+1 | <who issues it>; the nexus assigns |
```

When the nexus assigns an id it moves **Next free** in the same edit, so two sessions asking in one turn get two ids.

## `resources.md` — leases and numbered files

```markdown
## Exclusive resources
| Resource | Holder | Since | Limit | Queue |
|---|---|---|---|---|
| <resource> | <slug> | <time> | <time> | <slug>, <slug> |

## Sequence-numbered files
**Highest applied or merged:** <base branch> V<n> · <release branch> V<n> · production V<n> (checked <time>) — the next number is one above all three
| Session | Placeholder | Assigned at merge |
|---|---|---|
| <slug> | `V__pending_<slug>__<name>.sql` | V<n+1> on <date> |

## Scratch names and ports
| Session | Databases / ports / paths |
|---|---|
| <slug> | <its own names> |

## Read-only for everyone
- <the shared source no session may write to, and why>
```

## `owner-checks.md` — production checks that are the user's

Things no session may do and nobody but the user can confirm: a grant on a production login, a setting on the live server, a job's schedule in production. Sessions report them; the nexus collects them here so they don't stay scattered across logs.

```markdown
| # | Check | Why | From | Since | Done |
|---|---|---|---|---|---|
| 1 | <what to look at, where> | <what breaks if it's wrong> | <slug> | <date> | ☐ |
```

## `sessions/<slug>.md` — a stage log

The session's own record, appended every turn. The nexus judges the PR on this file. The format of each block is in [contract.md](contract.md).

```markdown
# <slug> — <slice>
**Worktree:** <path> · **Branch:** <branch> · **PR:** #n · **Parent:** — or <owner slug> · **Scratch:** <names>

## <stage> — <date time>
<what was done, the evidence: commands, counts, commits>

**Status:** <stage> · <working | waiting | blocked | done>
**Waiting on:** …
**Next:** …
**Head:** `<sha>`

## From nexus — <date time>
<the nexus's message, as sent>
```
