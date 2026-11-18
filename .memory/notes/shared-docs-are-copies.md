---
name: shared-docs-are-copies
description: A reference doc several skills share is a committed copy in each skill, synced from one source, because the skills CLI drops symlinks that leave a skill folder
type: decision
source: skills/shared.json, .github/scripts/sync_shared.py, user 2026-11-18
verified: 2026-11-18
volatility: low
---

Until 2026-11-18 the database and networking skills, and incident-fix, shared docs and
`skills/networking/netaudit/scripts/netgraph.py` through relative symlinks. `npx skills add` (skills@1.9.0) skips any symlink that
points outside the skill folder (`SKILLS_SYMLINK_OUTSIDE_SKILL`), so installed skills silently
lacked the docs their SKILL.md tells them to read. The user weighed four options: copies synced
from one source, a generated install branch, sibling paths such as ../dbaudit/theory.md, and a
shared reference skill. They chose synced copies, the only option where a single-skill install
is complete.

Don't reintroduce a symlink under `skills/`: check_repo fails on one. To share a file, add it to
`skills/shared.json` and run `sync_shared.py`. Edit only the source; the script won't overwrite
an edited copy. The copies carry no header, so their bytes, and every recorded `skill_hash`,
match the old symlinked tree.
