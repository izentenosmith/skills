# Parallel tracks — a tree of sessions

Open this when a slice's brief lists **Parallel tracks**, or when you are the session that owns such a brief. The rules it refers to — briefing, the PR gate, cleanup — are in [SKILL.md](SKILL.md) and `setup.md`.

A PR whose brief lists **Parallel tracks** (agent-brief writes them only when each track has its own write area, needs nothing another track builds, and meets the others only at seams the brief fixed) can be built by several sessions at once. The session that owns the brief becomes the **nexus of its tracks**: this skill, one level down.

The owner is still a building session — it writes the shared part and integrates — that also coordinates its tracks: it takes this skill's briefing, gate and cleanup rules for its children, not the no-product-code rule, which belongs to the root nexus.

1. **The owner builds the shared part first:** the brief's approval, the acceptance tests, and track 0 — the seams the tracks meet at — committed on the PR branch.
2. **One child session per track**, each in its own worktree branched from that commit, briefed with the contract plus its track: its criteria, its area, the brief's path to read and not write. Each child runs tdd on its track, then refactor-review, devils-advocate and tyr-verdict on its own diff, to a GO at its head.
3. **The owner gates each track** exactly as you gate a PR — GO on the head, in its area and nothing else, findings settled, counts with the skipped number — merges it into the PR branch, and ticks the brief's criteria from the child's log.
4. **Then the owner integrates:** the whole suite and the acceptance tests on the merged branch, then devils-advocate and tyr-verdict on the combined diff. Defects that live between tracks — shared state, a fixture two tracks both changed, an ordering — are found here or not at all. Its GO is the PR's GO, and the PR comes to you like any other.

The tree has **one root**: registries, the register, leases and the user stay with the top nexus. A child's question goes to its owner, which answers it from the brief or forwards it up; a child never asks the user and never takes a number. Every session, at any depth, keeps its log in the same notes folder, with its parent named in `status.md`.

**Cleaning up a track's child.** It has no PR of its own: it says `done` when its owner has merged its track into the PR branch, and its owner cleans it up then, by the checks in `after-merge.md` (section "Cleanup — when a session's work is merged"); the owner is cleaned up by the root nexus once the PR is merged.
