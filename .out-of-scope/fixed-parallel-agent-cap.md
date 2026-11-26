# A fixed cap of four parallel agents

**The idea.** The development flow runs at most four sessions or workers at once: nexus started "at
most four" sessions, and `harness/loop.py` and `harness/pipeline.py` defaulted to `--concurrency 4`.

**Why it's out.** Four was a fixed number with no cause behind it, so slices that were ready waited
for a slot for no reason the work could name. On 2026-11-19 the owner asked for no enforced limit
in the development harness ("leave it free"), and `6aa68a2` took it out. nexus now starts every
slice that is ready and holds one back only for a named reason (a dependency, disk, or a limit the
user set, recorded as a decision); `fan_out` reads a concurrency of 0 as one worker per job, the
new default for `loop.py` and `pipeline.py`. The other harnesses and `evals/run.py` still default
to 4: the request named the development flow only. See `.memory/notes/no-fixed-parallel-cap.md`.

**What would reopen it.** A run that failed because too many sessions ran at once (a rate limit,
memory or disk running out), and then a limit set for that cause, not a fixed four.
