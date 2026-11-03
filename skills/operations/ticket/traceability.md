# Traceability — commits, PRs, comments and hours

An item that says "done" with nothing pointing at the change is a claim; one that names the commits is evidence. This doc covers what links an item to the work, and the one field most often filled with fiction — hours.

## Commits and PRs

**In the description**, for any item whose work is implemented, end with the trace:

- **Commits:** the short SHAs · **PR:** its link · **Scope:** files changed and lines added/removed, from `git show --stat --format='' <sha> | tail -1` (summed across commits)
- **Continues** `<id>` — when this item picks up where another left off

**As a real link on the item**, where the tracker integrates with the code host. Prefer the **mention convention** when the integration exists, because it maintains itself: the commit message or PR description names the item, and the tracker links it on push. The adapter gives the syntax (`AB#123` for Azure Boards, the issue key for Jira, the issue identifier or a magic word such as `Fixes ABC-123` for Linear). It only works if the mention is in the message **before** the push — rewriting buried commits to add it isn't worth a rebase. Where the integration doesn't exist, add the link through the API, and only for commits that are already pushed — the tracker can't resolve a SHA the code host doesn't have yet.

**Find the commits** for a piece of work with `git log --oneline --since=<date> -- <paths>`, `git log --grep=<keyword>`, or the merge commit's PR. When documenting a range, group commits into one item per user-visible change, not one per commit.

## Closing comments

Every close and every state change that isn't routine adds a comment: what was done, the commits or PR, and where it was verified. The comment is what a reader finds six months later; the state change alone says nothing.

## Hours and estimates

Some teams track hours worked; some track estimates in points or a scale; many track neither. The profile says which, and the field.

**Never invent hours silently.** The number reflects effort and complexity, not volume of code — a 500-line change can be an hour of work and a one-line fix a day. Git timestamps are not a measure either: a rebase gives every commit the same commit date.

When hours are needed:

1. **Calibrate against the user's own history** — query their closed items with hours, and note the range and median.
2. **Propose a number** by comparison to similar closed items, and **say it is an estimate** and what it was compared to.
3. **Wait for the user to confirm or correct it.** On an item still open, the number is hours *to date*.

A typical calibration table, built from the team's history rather than this example:

| Reference | Hours |
|---|---|
| Trivial UI adjustment, one-line fix | 0.5 |
| Contained fix, simple visual improvement | 1 |
| Medium feature, refactor with a migration | 2 – 2.5 |
| Large multi-commit feature | 4 – 5.5 |
| Critical incident | the logged response time |

For trackers with no hours field (Linear has estimates but no time tracking), don't simulate one in comments unless the team already does.
