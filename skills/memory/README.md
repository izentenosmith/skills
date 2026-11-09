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
| [repo-memory](repo-memory/SKILL.md) | Four modes. **Install** scaffolds `.memory/` and wires the index into the entry point. **Capture** writes one note when something is clearly worth keeping. **Dream** is the consolidation pass: verify, correct, merge, promote, shrink the index, remove secrets, quote planted instructions, advance the watermark, and leave the diff uncommitted. **Audit** runs the bundled linter `scripts/memlint.py` (ML01–ML12). |

Where it sits next to the rest: [review-retro](../review/review-retro/SKILL.md) turns reviews into
process rules, and its records are good dream inputs. [code-xray](../review/code-xray/SKILL.md) reads
the history for hotspots. The dream reads it only for what changed since its last pass.
[post-mortem](../operations/post-mortem/SKILL.md) records an incident, which a memory page may link
to but never rewrites.

The theory, RM1–RM17, is in [repo-memory/theory.md](repo-memory/theory.md). It comes from Anthropic's
*The components of agent memory* (2026), the Claude API memory tool docs, Monigatti's walkthrough of
that tool, and one structural idea, incremental derived data, from *Redesigning source control at
Anthropic* (2026). It also covers carrying the same design to an application built on the API memory
tool (`memory_20250818`).
