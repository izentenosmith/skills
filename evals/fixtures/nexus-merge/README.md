# Harbor Bikes — the counter app, mid-increment

```
repo/        the main checkout (git, branch main); the shared notes are in repo/.workflow/nexus/
wt/<slug>/   one worktree per session, on the session's branch
scripts/gh   the forge, offline: gh's pr subcommands (list, view, checks, diff, merge, comment),
             answered from repo/'s branches; every call is recorded in scripts/.calls.log
```

GitHub can't be reached from this machine: `scripts/gh` is the forge here. The repository and its
worktrees are built by `make-history.sh`, which `evals/setup.sh` runs.
