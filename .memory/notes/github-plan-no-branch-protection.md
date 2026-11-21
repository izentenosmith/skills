---
name: github-plan-no-branch-protection
description: main is protected by an active ruleset since the repo went public on 2026-11-20; before that, private on GitHub Free, the ruleset was only a record. Auto-merge is still off
type: fact
source: gh api repos/izentenosmith/skills/rulesets, .github/rulesets/main.json, user 2026-11-20
verified: 2026-11-21
volatility: high
---

The user made the repo public on 2026-11-20. `gh api repos/izentenosmith/skills/rulesets` now
returns ruleset `main` (id 25805362) with `enforcement: active` on the default branch: pull request
required (0 approvals), five required status checks (skills, links and eval wiring; harness tests on
Python 3.13 and 3.14; eval controls; memory audit, checked 2026-11-21), no force push, no deletion, no bypass actors. So red CI now
blocks a merge, and a direct push to `main` is refused.

Still true: `allow_auto_merge` is `false` in the repo settings, so `gh pr merge --auto` fails;
merge by hand once the checks are green. The classic branch-protection endpoint
(`.../branches/main/protection`) returns 404 "Branch not protected": the ruleset is the protection.

**History:** until 2026-11-20 the repo was private on GitHub Free, where both endpoints returned
HTTP 403 and `.github/rulesets/main.json` was a record that nothing enforced. Anything written in
that period that says "check CI yourself before merging, nothing blocks it" is out of date.
