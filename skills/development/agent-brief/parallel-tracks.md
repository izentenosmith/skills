# Parallel tracks — when a brief splits

> Read this only when the design's decomposition or the brief's size suggests the work could split.
> Otherwise the brief keeps its one line, `**Parallel tracks:** none — <why>`, and you are done.

A big build sometimes splits into groups of criteria that several sessions can build at once, each working towards its own GO, with the session that owns the brief integrating them. Usually it doesn't, and the brief says so in one line.

## The four tests

A group of criteria is a **track** only when all four hold:

1. **Its writes are its own.** No module, file, migration or shared document is changed by two tracks. Name each track's area — the module or package, not file paths.
2. **It needs nothing another track builds.** Every criterion in it is observable without another track's behavior.
3. **The seams between tracks are fixed here.** Any interface that two tracks meet at is decided in **Key interfaces** and built first, as track 0, before the others start.
4. **It is worth a session.** Several slices at least. A session per track plus an integration pass costs more than a small build saves.

When in doubt, keep one track. Tracks that could each ship as their own PR are really increments, and belong in architect-deep-dive's decomposition.

## How the brief lists them

Only when every track passes the four tests, the brief's one-line `**Parallel tracks:** none — …` is replaced by:

```markdown
**Parallel tracks:**
- **Track 0 — seams:** <the interfaces the tracks meet at>; built first, before any other track starts
- **Track A — <name>:** criteria <which>; area <module/package>; needs track 0 only
- **Track B — <name>:** criteria <which>; area <module/package>; needs track 0 only
- **Integration:** the owner of this brief merges each track at its GO, runs the whole suite and the acceptance tests, then runs devils-advocate and tyr-verdict on the combined diff
```

The tracks are part of what the user approves: show them at the approval gate with the criteria.
