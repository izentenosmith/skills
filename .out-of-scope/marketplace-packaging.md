# Packaging skills as zips for a marketplace

**The idea.** A packager (`marketplace/`, added in `30b98e0`) built one standalone zip per
skill, plus bundles, for listing on a third-party skills marketplace. At package time it copied in
the docs other skills owned, turned links to sibling skills into names, and applied text edits from
`marketplace/patches.json` that removed harness-only sections. CI ran the packager's checks, and
`evals/run.py` could stage a skill from its zip.

**Why it's out.** It made a second, rewritten copy of every skill that was not the one in the repo.
A zip shipped the repo text with the patches applied, so a score earned on the repo held for the
zip only as long as every patch stayed harmless; and the packager, its patches file, a CI step and
a staging mode in `run.py` all had to keep step with every skill edit. Removed, with every
reference to it, in `1c9581f` (2026-11-17). Installs now go through the `skills` CLI or the Claude
Code plugin, both straight from the skill folders: the repo has no installer of its own (README,
Conventions), and a skill folder stands alone without being rewritten. `check_repo.py` still warns
about scores staged through "the zip-packaging step this repo no longer has".

Not to be confused with `.claude-plugin/marketplace.json`, the Claude Code plugin manifest, which
installs the skill folders as they are.

**What would reopen it.** A place people install from that can't take a skill folder as it is,
and a failure a user hit because of it.
