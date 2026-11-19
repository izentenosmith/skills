---
name: no-fixed-parallel-cap
description: The development flow sets no fixed limit on parallel agents — nexus starts every ready slice, and loop.py and pipeline.py default to --concurrency 0
type: decision
source: skills/development/nexus/SKILL.md, harness/loop.py::fan_out, user 2026-11-19
verified: 2026-11-19
volatility: low
---

Until 2026-11-19 nexus ran "at most four" sessions at once and `harness/loop.py` and
`harness/pipeline.py` defaulted to `--concurrency 4`. The user asked for no enforced limit of four
agents in the development harness: "leave it free".

Nexus now starts every slice that is ready and holds one back only for a named reason (a
dependency, disk, or a limit the user set, recorded as a decision). `fan_out` treats a concurrency
of 0 as one worker per job, and 0 is the default for `loop.py` and `pipeline.py`. Don't
reintroduce a default cap there. The other harnesses (`fix.py`, `prreview.py`, the database and
network ones) and `evals/run.py` still default to 4: the request named the development flow only.
