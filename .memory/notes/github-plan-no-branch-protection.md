---
name: github-plan-no-branch-protection
description: main has no enforced protection: the repo is private on GitHub Free, so rulesets, branch protection and auto-merge are unavailable
type: fact
source: .github/rulesets/main.json, user 2026-11-10
verified: 2026-11-18
volatility: high
---

`gh api repos/izentenosmith/skills/rulesets` and `.../branches/main/protection` return HTTP 403
"Upgrade to GitHub Pro or make this repository public", and setting `allow_auto_merge=true` is
silently left `false`. So `.github/rulesets/main.json` is a record, not applied: its required checks
don't block a merge, and `gh pr merge --auto` fails. The user chose on 2026-11-10 to leave both off
rather than upgrade or go public. Check CI yourself before merging.
