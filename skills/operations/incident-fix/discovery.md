# Discovery — learning the repo before touching it

Nothing environment-specific is assumed. Every command, convention and destination comes from the repo itself, or from one question to the user. The output is a short profile, `.workflow/env.md`, so the next fix in this repo starts from it instead of from zero.

## Is there a current profile?

If `.workflow/env.md` exists, check it is still true before trusting it:

- [ ] Its **recorded commit** is an ancestor of `HEAD`.
- [ ] **None of the files it was derived from changed since** — `git diff --name-only <recorded commit> HEAD` against its *Sources* list (manifests, CI config, instruction files).
- [ ] **Each command it names still resolves** — the script, target or task exists.

All three hold → step 0 is a one-line confirmation. Any fails → re-discover the stale parts, not the whole profile.

## What to read, in order

1. **Agent and contributor instructions** — `CLAUDE.md`, `AGENTS.md`, `.cursor/rules`, `CONTRIBUTING.md`, the README's development section, any `docs/` page about releasing or deploying. **What these authorize or forbid overrides everything below** — including whether you may push, merge or create tickets without asking.
2. **CI configuration** — whatever workflow, pipeline or job files the repo has. **CI is the ground truth for commands**: the command a pipeline runs is the one the project actually trusts, and it often differs from the obvious one (`test:ci` vs `test`, a wrapper script, extra flags, a service container the tests need).
3. **Build manifests and task runners** — package manifests, build files, Makefile / justfile / taskfile, scripts directories. Use them to fill what CI doesn't show, never to override what it does.
4. **Git history** — recent merges vs. squash commits vs. direct pushes, branch names, commit message conventions (ticket keys, conventional-commit prefixes, `Fixes #` links).

## What to find

| Item | How you know | If it isn't there |
|---|---|---|
| **Test command** (full + focused) | CI job, then manifest scripts | Ask. If there are no tests at all, say so — the fix then ships with the smallest runnable check that fails without it |
| **Lint / type-check / format** | CI job, config files at the root | Record "none" — don't invent a linter |
| **Build command** | CI job, manifest | Record "none" for interpreted code without a build |
| **Merge convention** | Instructions, then history: PR merges, squash, direct pushes, protected-branch hints | Ask |
| **Does CI run the tests?** | A test step in the CI config | Record "no" — local runs are then the only gate, and the final checklist says so |
| **Pre-production environment** | Instructions, deploy config, environment names in CI, branch-per-environment patterns | Record "none" — production verification is then the only verification |
| **Ship mechanism** | Release/deploy jobs, tags, publish steps | Ask |
| **Tracker** | **Evidence only**: ticket keys in commit messages, tracker links in docs or PR templates | Use a local markdown log in `.workflow/` — never invent a tracker |
| **Installed skills** | The skills directories the agent loads from | Use the fallback checklist for that step |

**Installed skills to look for**, by the phase they'd cover: a design skill (`architect-deep-dive`) and the build-and-review pipeline (`tdd`, `refactor-review`, `devils-advocate`, `tyr-verdict`) for Phase 3, a deployment-rules or release skill for promotion, a ticket-creation skill for the incident item and follow-ups, `post-mortem` for Phase 4, and the repo's own dev-criteria or conventions skill throughout. **Delegate to what's there instead of duplicating it**, and say which you used.

## Ask once

Collect every item you couldn't discover into **one** question, with your best guess for each so the user can just confirm. Then offer to append the answers to the repo's agent instructions file, so the next session discovers them instead of asking.

## Incident additions

An incident needs four more things the hotfix lane doesn't. Find each **before** Phase 1 — containment options you discover mid-outage get skipped.

### Rollback and containment levers

| Lever | Where it shows up | Check |
|---|---|---|
| **Previous deployable version** | Release tags, image tags, artifact versions, deploy history in CI | Is it still deployable — did a forward-only migration ship since? |
| **Feature flags and runtime config** | A flag client in the code, config files or env vars read at runtime, an admin endpoint | Does a flip take effect without a deploy? How fast? |
| **Scaling and scheduled jobs** | Deployment manifests, job schedulers, cron definitions, worker configs | Can the job be paused without losing its queue? |
| **Revertable commits** | The git range since the last good deploy | Does reverting require a deploy, and does the deploy path work right now? |
| **Secret rotation** | Where credentials are referenced: env, a secrets manager, config | Who can rotate, and what restarts afterwards? |
| **Traffic controls** | Load balancer, gateway or maintenance-mode switches the repo references | What do users see while it's on? |

For each lever found: **what it stops, what it costs users, how long to undo, who can pull it.** A lever nobody here can pull is still worth listing — it tells the user whom to call.

### Observability

What is reachable **from this environment**: log and metrics CLIs that are installed and authenticated, connected tools, dashboards or runbooks the repo links to, error-tracking clients in the code (which tell you where errors are sent). **If nothing is reachable, ask the user for logs, screenshots or exports** — and say which ones, for which time window.

### Data access mode

**Read-only, unless the user says otherwise for a specific action.** Note how data can be reached (a read replica, a read-only role, an export, a local copy) and prefer the one that cannot write. Every production write — repair, backfill, cleanup — is its own confirmed action under the data-repair checklist.

### Where the incident log lives

The log must be **durable**: committed to the repo, or in the tracker — **never only** in a scratch directory or an uncommitted worktree. Look for an existing incidents or postmortems folder (`docs/incidents/`, `postmortems/`, a wiki path in the docs). If there isn't one, propose `docs/incidents/<YYYY-MM-DD>-<slug>.md` as part of the single discovery question.

## The profile — `.workflow/env.md`

```markdown
# Environment profile
- **Recorded:** <UTC date> at <commit sha>
- **Sources:** <the files this was derived from — instructions, CI config, manifests>

## Commands
- **Test (full):** <command> — <where it came from>
- **Test (focused):** <how to run one test or file>
- **Lint / type-check:** <commands, or "none">
- **Build:** <command, or "none">

## Conventions
- **Merge:** <PR to main with required checks | direct push | …>
- **CI runs tests:** <yes / no>
- **Environments:** <pre-production names and how to reach them, or "none">
- **Ship:** <how a change reaches production>
- **Tracker:** <name and link pattern, or "local log in .workflow/">
- **Commit message convention:** <…>

## Installed skills
- <step> → <skill name>

## Authorized without asking
- <only what the repo's instructions explicitly allow — usually nothing>

## Incident levers
- **Previous version:** <how to redeploy it, and whether a migration blocks it>
- **Flags / config:** <what can be flipped at runtime, and how>
- **Jobs / scaling:** <what can be paused or scaled down, and how>
- **Secret rotation:** <where, by whom>
- **Observability:** <reachable tools and dashboards, or "ask the user">
- **Data access:** <read-only path; who can approve writes>
- **Incident logs live in:** <path or tracker>
```

It is a working file like the brief and the ledger: gitignore `.workflow/` or commit it — but if you commit it, it's a record a teammate can correct.
