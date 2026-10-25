# Release-notes fixture — `release-notes`

Inputs for writing the notes of a shipped release: the product's git repository
(squash-merged, one commit per PR, tagged releases) and an export of its issue
tracker.

```
make-history.sh   builds repo/ (gitignored — it is a nested git repo)
repo/             Beacon, an uptime-monitoring SaaS, tagged v2.2.0, v2.3.0, v2.4.0
issues/           the tracker issues the commits link to
```

Build it with `../../setup.sh`, or directly:

```bash
./make-history.sh
```

What is planted, and what a correct run does, is in `../release-notes.answers.md`
— outside this folder, because everything in it is copied into the run.
