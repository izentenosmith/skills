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
| **Test command** (full + focused) | CI job, then manifest scripts | Ask. If there are no tests at all, say so — the lane writes a runnable check instead |
| **Lint / type-check / format** | CI job, config files at the root | Record "none" — don't invent a linter |
| **Build command** | CI job, manifest | Record "none" for interpreted code without a build |
| **Merge convention** | Instructions, then history: PR merges, squash, direct pushes, protected-branch hints | Ask |
| **Does CI run the tests?** | A test step in the CI config | Record "no" — local runs are then the only gate, and the final checklist says so |
| **Pre-production environment** | Instructions, deploy config, environment names in CI, branch-per-environment patterns | Record "none" — production verification is then the only verification |
| **Ship mechanism** | Release/deploy jobs, tags, publish steps | Ask |
| **Tracker** | **Evidence only**: ticket keys in commit messages, tracker links in docs or PR templates | Use a local markdown log in `.workflow/` — never invent a tracker |
| **Installed skills** | The skills directories the agent loads from | Use the fallback checklist for that step |

**Installed skills to look for**, by the step they'd cover: a TDD skill (Step 3), a code-review or adversarial-review skill (Step 4 — `devils-advocate` and `tyr-verdict` in this collection), a deployment-rules or release skill (Step 6), a ticket-creation skill (Step 5), and the repo's own dev-criteria or conventions skill (all steps). **Delegate to what's there instead of duplicating it**, and say which you used.

## Ask once

Collect every item you couldn't discover into **one** question, with your best guess for each so the user can just confirm. Then offer to append the answers to the repo's agent instructions file, so the next session discovers them instead of asking.

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
```

It is a working file like the brief and the ledger: gitignore `.workflow/` or commit it — but if you commit it, it's a record a teammate can correct.
