# Sharing reference docs through symlinks

**The idea.** A reference doc several skills use (the database and networking docs, networking's
`netgraph.py`, docs incident-fix shares) lives once, and each skill folder links to it with a
relative symlink.

**Why it's out.** Installs broke silently. `npx skills add` (skills@1.9.0) skips any symlink that
points outside the skill folder (`SKILLS_SYMLINK_OUTSIDE_SKILL`), so 13 installed skills lacked the
docs their SKILL.md tells them to read, and the four networking skills lost `scripts/netgraph.py`.
Nothing failed at install time; the skill just ran without its references. Replaced in `9147ebb`
(2026-11-18): each of the 31 links became a committed copy, synced from one source listed in
[skills/shared.json](../skills/shared.json) by `.github/scripts/sync_shared.py`, and `check_repo.py`
now fails on any symlink under `skills/`. Sibling paths (`../dbaudit/theory.md`) and a shared
reference skill were weighed too and turned down: only copies leave a single-skill install complete.
See `.memory/notes/shared-docs-are-copies.md`.

**What would reopen it.** Every installer this repo supports keeping links that leave a skill
folder, shown by a single-skill install that has every doc its SKILL.md names.
