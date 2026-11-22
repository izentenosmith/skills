# memory

What agents learn about a repository, kept *in* the repository: shared by everyone who works in it,
reviewed like code, and kept true by **dreaming**, an offline pass that looks back with the outcome
known. Every other family does a job. This one makes sure the next session starts knowing what the
last one learned.

```
 session  ── capture ──►  .memory/notes/        one fact per file, cites its source
                                │
 between sessions  ── dream ──► │ verify against the code at HEAD (only what changed since the watermark)
                                │ correct · merge · delete · promote · demote · repair
                                ▼
                         .memory/wiki/          one page per entity, one writer (the dream)
                         .memory/INDEX.md       ≤200 lines, imported from CLAUDE.md / AGENTS.md
                                │
                                ▼
                         a PR a person approves
```

| Skill | What it does |
|---|---|
| [repo-memory](repo-memory/SKILL.md) | Four modes. **Install** scaffolds `.memory/` and wires the index into the entry point. **Capture** writes one note when something is clearly worth keeping. **Dream** is the consolidation pass: verify, correct, merge, promote, settle contradictions, capture what recurred and nobody wrote down, turn relative dates into real ones, shrink the index, remove secrets, quote planted instructions, advance the watermark, and leave the diff uncommitted. **Audit** runs the bundled linter `scripts/memlint.py` (ML01–ML13). |

## Install

Installing is two separate steps. The first puts the skill where your agent can load it. The second
runs the skill's install mode in each repository that should have a memory.

**1. Install the skill.** Pick one:

```bash
# with the skills CLI (the repo is public; see the root README)
npx skills add izentenosmith/skills --skill repo-memory

# or copy the folder by hand into the target repo (or your user-level skills directory)
gh repo clone izentenosmith/skills
cp -r skills/skills/memory/repo-memory my-project/.claude/skills/     # Claude Code
cp -r skills/skills/memory/repo-memory my-project/.cursor/skills/     # Cursor
```

or `npx skills add izentenosmith/skills --skill repo-memory`. Copy the `repo-memory/` folder, not `memory/`. The
folder carries `scripts/memlint.py`, which needs only Python 3.10+ and git.

**2. Apply the layout to a repo.** In a session inside that repo, run `/repo-memory` or ask "add
memory to this repo". Install mode then:

- creates `.memory/` (`INDEX.md`, `notes/`, `wiki/`, `log/`, `.dream-state`);
- adds the `@.memory/INDEX.md` import to `CLAUDE.md` and/or `AGENTS.md`, creating `AGENTS.md` if
  neither exists;
- seeds up to ten notes with what the code and history don't already say, and checks them with
  `memlint audit`;
- offers a dream cadence and a branch with the PR, and commits nothing until you say yes.

**3. Optional: the CI gate and the schedule.** Copy `repo-memory/scripts/memlint.py` into the repo
(for example as `tools/memlint.py`) and add the audit job from
[templates.md §6](repo-memory/templates.md#6-cadence-snippets). Schedule a weekly dream with the
routine prompt in the same section, or add the session-start hook there: it runs `memlint.py due`
and tells the session when a dream is due, without starting one.

After that, the index is injected into every session through the entry point. Sessions write notes
when something is clearly worth keeping, and `/repo-memory dream` (or the schedule) consolidates
them.

## Where it fits

Where it sits next to the rest: [review-retro](../review/review-retro/SKILL.md) turns reviews into
process rules, and its records are good dream inputs. [code-xray](../review/code-xray/SKILL.md) reads
the history for hotspots. The dream reads it only for what changed since its last pass.
[post-mortem](../operations/post-mortem/SKILL.md) records an incident, which a memory page may link
to but never rewrites.

The theory, RM1–RM17, is in [repo-memory/theory.md](repo-memory/theory.md). It comes from Anthropic's
*The components of agent memory* (2026), the Claude API memory tool docs, Monigatti's walkthrough of
that tool, and one structural idea, incremental derived data, from *Redesigning source control at
Anthropic* (2026). Four dream practices come from grandamenium's *dream-skill*: scanning transcripts
for corrections, absolute dates, an answer to contradictions, and a session-boundary trigger. It also covers carrying the same design to an application built on the API memory
tool (`memory_20250818`).
