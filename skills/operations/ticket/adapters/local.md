# Adapter — local markdown log

When discovery finds no tracker, the work items live in the repository: **`.workflow/backlog.md`**, committed with the change that creates or updates them, so items travel with the code. Never invent a tracker, and never keep the log only in an uncommitted worktree or a scratch directory.

## Format

```markdown
# Backlog

### L-7 · Invoice totals match the sum of their lines
- **Kind:** bug · **State:** todo · **Labels:** prod-incident, cause:data
- **Created:** 2026-10-15 · **Updated:** 2026-10-15 · **Owner:** <who, or "unassigned">
- **Continues / duplicates / blocks:** <L-n, or none>

<description from writing.md>

**Log**
- 2026-10-15 · created · from incident docs/incidents/2026-10-15-tax-totals.md
- 2026-10-16 · done · fixed in 3f2a1c4; verified on staging
```

## Rules

- **Ids are `L-<n>`**, sequential, never reused — read the highest existing id before adding one.
- **States:** `todo` · `doing` · `done` · `canceled`. Labels use the canonical names in [labels.md](../labels.md).
- **Append to an item's log; don't rewrite history.** A state change is a new log line with its date and evidence.
- **Searching** is `grep` over the file: by title words, by label, by `State: todo`.
- **Read back** by re-reading the item from the file after writing it.
- **Commit** the file with the change it belongs to, and reference the id in the commit message (`refs L-7`).

If a tracker is adopted later, migrate open items through the real adapter and mark each local item `canceled` with a log line pointing at its new id.
