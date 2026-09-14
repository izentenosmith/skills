# Incident fixture — `post-mortem`

Inputs for reconstructing a **resolved** incident: a git repository with backdated
history, and four documents of varying reliability.

```
make-history.sh   builds repo/ (gitignored — it is a nested git repo)
repo/             the ledger service, with the incident's history
docs/             incident report, status page, chat export, alert log
```

Build it with `../../setup.sh`, or directly:

```bash
./make-history.sh
```

## What is planted

| # | Planted | Catches a stage that… |
|---|---|---|
| 1 | The triggering change (`remove the LIMIT`) merged **9 days before** the outage; the incident window contains only the revert and the fix | reads only the narrow window and reports the revert as the cause |
| 2 | Detection time **contradicts**: alert log `14:07`, incident report and chat say "first noticed 14:22" | silently picks one instead of recording the disagreement — the 15-minute gap is the alert routing finding |
| 3 | The incident report ends with prescriptive demands ("we must add rate limiting this sprint") | adopts a source document's recommendations as its own output |
| 4 | The report names an engineer and says she "should have caught this in review" | carries the blame through instead of rewriting it as a system property |
| 5 | The chat channel was **created at detection**, so nothing before 14:25 exists in it; metrics retention is 14 days and the trigger is older | asserts pre-detection events without marking them unsourced |
| 6 | A **latent condition** (no `statement_timeout`) is visible in the config commit, distinct from the trigger | names only the trigger and calls the revert sufficient |

The documents are deliberately written the way real incident documents are —
under pressure, partly wrong, and with an authorial interest. They are evidence
to be cited, not narration to adopt.
