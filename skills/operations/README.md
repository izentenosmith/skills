# operations

Four skills for a system that is already running and already shipped. Three of them form a response chain; the fourth stands alone.

```
hotfix ──escalates──► incident-fix ──hands its log to──► post-mortem      release-notes
 (urgent, not down)    (contain → diagnose → fix → learn)  (the record)     (stands alone)
```

## The skills

| Skill | What it does |
|-------|--------------|
| [hotfix](hotfix/SKILL.md) | A fast, still-disciplined lane for an urgent bug in a system that is **up**. Discovers the repo's commands and conventions, routes outages and design questions out, proves the bug with a red test, fixes it once at the shared cause, runs one adversarial pass — blocking on data, money, permissions and tenancy — and ships by the repo's convention with recorded evidence. |
| [incident-fix](incident-fix/SKILL.md) | Production incidents end to end. Contains first with ranked, reversible levers; diagnoses read-only and sizes the impact with a reproducible count; fixes through the review pipeline capped at two loops, with any data repair as its own audited artifact; then hands the log to post-mortem and runs the **follow-through** — every contributing factor becomes an owned follow-up or an explicitly accepted risk. Every production action waits for its own confirmation. |
| [release-notes](release-notes/SKILL.md) | Reads the change set from git, classifies every change (including an explicit **drop** bucket for anything with no user-visible effect), and translates each survivor from what was built into what the reader can now do. Depth matched to scope; breaking changes above the fold. |
| [post-mortem](post-mortem/SKILL.md) | Reconstructs a **resolved** incident into a blameless written record — timeline built from a git history date range plus incident docs and PDFs, quantified impact, and contributing factors rather than a single root cause. |

## How to use them

Install all four from the root of the repo you're working in:

```bash
npx skills add izentenosmith/skills --skill hotfix incident-fix post-mortem release-notes
```

Just the response chain:

```bash
npx skills add izentenosmith/skills --skill hotfix incident-fix post-mortem
```

Or one at a time:

| Skill | Install |
|---|---|
| hotfix | `npx skills add izentenosmith/skills --skill hotfix` |
| incident-fix | `npx skills add izentenosmith/skills --skill incident-fix` |
| post-mortem | `npx skills add izentenosmith/skills --skill post-mortem` |
| release-notes | `npx skills add izentenosmith/skills --skill release-notes` |

Flags (`-a`, `-g`, `-y`) are in the [root README](../../README.md#install-with-npx). The harnesses below are not skills and need a clone.

Or **copy the folder you want into the repo you're working in**, alongside wherever that repo keeps its agent skills. Each folder is self-contained — `SKILL.md` plus its reference docs — so one folder is a complete install of one skill.

Then either let the agent trigger the skill when your request matches its `description`, or call it by name:

```
/hotfix   /incident-fix   /post-mortem   /release-notes
```

**`hotfix` and `incident-fix` hardcode nothing about your environment.** Build, test and lint commands come from your CI config; the merge convention from your instructions and history; the tracker only from evidence (otherwise a local log); rollback levers, observability and data access from what the repo and the machine expose. The result is cached in `.workflow/env.md`, which both skills share, and anything that can't be discovered is asked once, in one question.

**Both have harnesses** in [`harness/`](../../harness/README.md): `fix.py` runs the hotfix lane (or incident-fix's fix phase) from a bug report to a committed branch and, with `--open-pr`, a draft PR; `postmortem.py` runs Phase 4 from a resolved incident log to a linted post-mortem. Neither runs containment — that needs a person at every step.

**Both stop before anything outward-facing** — push, merge, deploy, publish, a ticket, a flag flip, a data write — and wait for your confirmation, one action at a time.

**`post-mortem` takes inputs you have to supply**: a date range for the git history (`2026-08-03 12:00 UTC → 2026-08-04 10:00 UTC`) and whatever incident documentation exists — the incident report, a vendor PDF, a chat export, alert emails, monitoring screenshots. It reconstructs from those; it cannot reconstruct from a description of the incident alone.

`release-notes` takes a range too, usually a tag pair (`v2.3.0..v2.4.0`) or a date window.

## The response chain's boundaries

- **hotfix routes out** the moment the system is down, data is being corrupted or exposed, or the fix turns out to need a design decision. A lane that keeps going past those is how a quick fix becomes an incident.
- **incident-fix contains before it diagnoses**, logs every step with clock-read UTC times in a log committed at each phase gate, and treats data repair as a separate artifact with a backup, a dry run and before/after counts.
- **post-mortem stays descriptive.** incident-fix's follow-through — owners, dates, accepted risks — is written *after* the record, separately, so the record never bends toward a fix it is arguing for.

## What post-mortem and release-notes have in common

**Both are written for someone who is not reading your code**, and both are therefore mostly exercises in translation and in deciding what to leave out.

- `release-notes` translates commits into user outcomes, and **drops everything with no user-visible effect**. The drop bucket is the load-bearing part: every dropped entry is attention returned to the entries that matter, and a note listing a lint fix beside a new feature teaches readers the document is noise.
- `post-mortem` translates artifacts into a timeline, and **stops at describing**. It does not propose remediation, assign work, or recommend what to build — the incident is solved, and a document that reconstructs *and* prescribes has an incentive to shape the reconstruction toward the prescription.

Both also publish under a deadline rather than at completeness. Release notes are read in the days after a release and almost never after; a postmortem circulated in three days with two open questions beats a complete one in three weeks, because memories decay fast and log retention decays faster.

## Reference docs

| Doc | Used by |
|-----|---------|
| [discovery](hotfix/discovery.md) | hotfix, incident-fix (incident-fix's copy adds levers, observability, data access) — the `.workflow/env.md` profile |
| [root-cause-note](hotfix/root-cause-note.md) | hotfix — the three-line note and the caller sweep |
| [diagnosis](hotfix/diagnosis.md) | hotfix, incident-fix (symlinked) — a red loop before any theory, minimise, ranked falsifiable hypotheses, one probe at a time |
| [review-checklist](hotfix/review-checklist.md) | hotfix — the review pass without a review skill |
| [follow-up](hotfix/follow-up.md) | hotfix — what a band-aid owes |
| [final-checklist](hotfix/final-checklist.md) | hotfix — the closing record and what counts as evidence |
| [severity](incident-fix/severity.md) | incident-fix — incident vs. hotfix, and SEV levels |
| [incident-log](incident-fix/incident-log.md) | incident-fix — the durable, clock-stamped log and its rules |
| [data-repair](incident-fix/data-repair.md) | incident-fix — repairing what the bug wrote |
| [follow-through](incident-fix/follow-through.md) | incident-fix — every factor owned or accepted |
| [postmortem-fallback](incident-fix/postmortem-fallback.md) | incident-fix — the record when post-mortem isn't installed |
| [phase-gates](incident-fix/phase-gates.md) | incident-fix — each phase's exit condition, and the fix-review fallback |
| [anatomy](release-notes/anatomy.md) | release-notes — the six elements, the commit→outcome translation rules, a full template |
| [distribution](release-notes/distribution.md) | release-notes — depth to scope, when visuals earn their place, where to publish |
| [evidence-sources](post-mortem/evidence-sources.md) | post-mortem — reading a git range, incident PDFs, chat exports and monitoring into a sourced timeline |
| [blameless-culture](post-mortem/blameless-culture.md) | post-mortem — why blameless is a data-collection strategy, and the language patterns that break it |
| [contributing-factors](post-mortem/contributing-factors.md) | post-mortem — past single-root-cause; the categories to sweep and where to stop descending |

## Measured

`post-mortem` has an eval fixture and a scored assertion set in [`../evals/`](../../evals/README.md): a git repository whose triggering commit sits nine days before the outage window, plus four documents that contradict each other on detection time — one of which blames a named engineer and demands specific remediation. Submitting that incident report verbatim as the answer scores **3/10** on the assertions that test what this skill instructs. **First run (n=1): 1.00 against 0.60 for no skill.**

`hotfix` (evals 8–11: a Node service, a JVM service with no build tool, a Python script with no tests, and an outage it must route out) and `incident-fix` (evals 12–14: a containerized web app with feature flags, a batch job that corrupted rows, a library with no deploy step) have fixtures and assertions; both assertion sets separate a reference answer from a do-nothing one. **First runs:** hotfix 1.00, 1.00, 1.00 and 0.83 (n=3) against 0.00–0.71 for no skill; incident-fix 0.95 (n=3), 0.77 (n=3) and 1.00 against 0.43–0.60. Eval 13's two repair misses are the grader: it tries only `--apply`-style flags, and the runs' repair scripts also require `--expect N --backup-dir`.

`release-notes` has one too (eval 29): a tagged git history whose range hides a one-line breaking change, a feature shipped and reverted inside the release, a CVE fix among routine dependency bumps, an improvement nobody measured, internal class and ticket names in the commit subjects, and work committed after the tag. Reference, do-nothing and plausible-but-wrong controls separate as intended (`python3 evals/controls/make_controls.py --only 29`). **First run (n=1): 1.00 against 0.54 for no skill.**
