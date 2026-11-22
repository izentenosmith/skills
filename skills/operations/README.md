# operations

Six skills for a system that is already running and already shipped. Three of them form a response chain; release-notes stands alone; and two keep the tracker that holds the work — `ticket` writes to it for every other skill, `backlog` shapes and orders what's in it.

```
hotfix ──escalates──► incident-fix ──hands its log to──► post-mortem      release-notes
 (urgent, not down)    (contain → diagnose → fix → learn)  (the record)     (stands alone)
      │                        │                               │
      └──── follow-ups, incident items ──► ticket ◄── changes ── backlog
                                    (Linear · Azure DevOps · Jira)  (map · refine · health · order)
```

## The skills

| Skill | What it does |
|-------|--------------|
| [hotfix](hotfix/SKILL.md) | A fast, still-disciplined lane for an urgent bug in a system that is **up**. Discovers the repo's commands and conventions, routes outages and design questions out, proves the bug with a red test, fixes it once at the shared cause, runs one adversarial pass — blocking on data, money, permissions and tenancy — and ships by the repo's convention with recorded evidence. |
| [incident-fix](incident-fix/SKILL.md) | Production incidents end to end. Contains first with ranked, reversible levers; diagnoses read-only and sizes the impact with a reproducible count; fixes through the review pipeline capped at two loops, with any data repair as its own audited artifact; then hands the log to post-mortem and runs the **follow-through** — every contributing factor becomes an owned follow-up or an explicitly accepted risk. Every production action waits for its own confirmation. |
| [release-notes](release-notes/SKILL.md) | Reads the change set from git, classifies every change (including an explicit **drop** bucket for anything with no user-visible effect), and translates each survivor from what was built into what the reader can now do. Depth matched to scope; breaking changes above the fold. |
| [post-mortem](post-mortem/SKILL.md) | Reconstructs a **resolved** incident into a blameless written record — timeline built from a git history date range plus incident docs and PDFs, quantified impact, and contributing factors rather than a single root cause. A metadata block makes incidents countable by cause and time to detect; a review gate comes before publishing. |
| [ticket](ticket/SKILL.md) | Creates, updates, closes and logs time on work items in **Linear, Azure DevOps or Jira**, or in a markdown log when there's no tracker. Discovers the tracker's schema and the team's conventions into `.workflow/tracker.md`, reconciles against existing items before creating, confirms the change set, writes through one adapter per tool, and reads every write back. Owns the canonical labels — production incidents for DORA, causes, follow-up action types, unplanned work, toil. |
| [backlog](backlog/SKILL.md) | Four modes over a whole backlog: **map** an initiative into a story map with outcome-named release slices, **refine** the next slice into thin stories with acceptance criteria, **health**-check a backlog and board with a repeatable 0–10 score (oversized items, stale work, WIP, unplanned work, competing priorities, hidden dependencies, overdue follow-ups, error budget), and **order** it by class of service and cost of delay. Reads the tracker; every change goes through ticket. |

## How to use them

Install all six from the root of the repo you're working in:

```bash
npx skills add izentenosmith/skills --skill hotfix incident-fix post-mortem release-notes ticket backlog
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
| ticket | `npx skills add izentenosmith/skills --skill ticket` |
| backlog | `npx skills add izentenosmith/skills --skill backlog` |

The repo is public, so no GitHub account is needed; the flags (`-a`, `-g`, `-y`) are in the [root README](../../README.md#install-with-npx). The harnesses below are not skills and need a clone.

Or **copy the folder you want into the repo you're working in**, alongside wherever that repo keeps its agent skills. Each folder is self-contained — `SKILL.md` plus its reference docs — so one folder is a complete install of one skill.

Then either let the agent trigger the skill when your request matches its `description`, or call it by name:

```
/hotfix   /incident-fix   /post-mortem   /release-notes   /ticket   /backlog
```

**`hotfix` and `incident-fix` hardcode nothing about your environment.** Build, test and lint commands come from your CI config; the merge convention from your instructions and history; the tracker only from evidence (otherwise a local log); rollback levers, observability and data access from what the repo and the machine expose. Where `ticket` is installed, both hand it their tracker writes. The result is cached in `.workflow/env.md`, which both skills share, and anything that can't be discovered is asked once, in one question.

**Both have harnesses** in [`harness/`](../../harness/README.md): `fix.py` runs the hotfix lane (or incident-fix's fix phase) from a bug report to a committed branch and, with `--open-pr`, a draft PR; `postmortem.py` runs Phase 4 from a resolved incident log to a linted post-mortem. Neither runs containment — that needs a person at every step.

**Both stop before anything outward-facing** — push, merge, deploy, publish, a ticket, a flag flip, a data write — and wait for your confirmation, one action at a time.

**`post-mortem` takes inputs you have to supply**: a date range for the git history (`2026-08-03 12:00 UTC → 2026-08-04 10:00 UTC`) and whatever incident documentation exists — the incident report, a vendor PDF, a chat export, alert emails, monitoring screenshots. It reconstructs from those; it cannot reconstruct from a description of the incident alone.

`release-notes` takes a range too, usually a tag pair (`v2.3.0..v2.4.0`) or a date window.

## The tracker pair

- **`ticket` is the only writer.** Every other skill that owes the tracker something — hotfix's follow-up, incident-fix's incident item and follow-through, backlog's splits and re-orders — hands it to `ticket`, so the rules live once: discover the schema instead of guessing it, reconcile before creating, confirm the exact change set, read every write back.
- **Nothing about the team is hardcoded.** The tool, project, item types, states, required fields, sprint or cycle, labels, hours field and language are discovered from the tracker's API and its history, and cached in `.workflow/tracker.md` with the traps found along the way. The adapters hold what's true of each tool for everyone: Azure DevOps tags append rather than replace, Jira reaches a status only by transition, Linear has labels instead of issue types.
- **Production failures are labelled when they start.** `prod-incident` on the item, opened while the incident is open, is what change-failure rate and time-to-restore are built from; a `caused-by-<deploy>` label pins the culprit when it isn't the last deploy.
- **`backlog` reads, judges and proposes.** Its health score is repeatable against a dated snapshot, and nothing it recommends reaches the tracker without the user's confirmation, through `ticket`.

## The response chain's boundaries

- **hotfix routes out** the moment the system is down, data is being corrupted or exposed, or the fix turns out to need a design decision. A lane that keeps going past those is how a quick fix becomes an incident.
- **incident-fix contains before it diagnoses**, logs every step with clock-read UTC times in a log committed at each phase gate, and treats data repair as a separate artifact with a backup, a dry run and before/after counts. It declares early, names a commander and exit criteria, keeps a live state block above the append-only log, registers every temporary production change and undoes them in steps, and checks in every 30–60 minutes.
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
| [diagnosis](hotfix/diagnosis.md) | hotfix, incident-fix (a synced copy) — a red loop before any theory, minimise, ranked falsifiable hypotheses, one probe at a time |
| [review-checklist](hotfix/review-checklist.md) | hotfix — the review pass without a review skill |
| [follow-up](hotfix/follow-up.md) | hotfix — what a band-aid owes |
| [final-checklist](hotfix/final-checklist.md) | hotfix — the closing record and what counts as evidence |
| [severity](incident-fix/severity.md) | incident-fix — incident vs. hotfix, declaring early, SEV levels, impact against the error budget |
| [roles](incident-fix/roles.md) | incident-fix — commander, operations, communications, planning; scaled to a small team; handoffs |
| [containment-levers](incident-fix/containment-levers.md) | incident-fix — ranked levers, overload and cascading-failure responses, the stepped ramp back |
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
| [template](post-mortem/template.md) | post-mortem — the document's sections and the metadata block that makes incidents countable |
| [review-checklist](post-mortem/review-checklist.md) | post-mortem — the review before publishing, and reusing records afterwards |
| [profile](ticket/profile.md) | ticket — the `.workflow/tracker.md` project profile and where each value is discovered |
| [writing](ticket/writing.md) | ticket — titles and descriptions per kind: story, bug, spike, task, incident, follow-up |
| [labels](ticket/labels.md) | ticket — the canonical labels: production incidents, causes, action types, unplanned work, toil |
| [traceability](ticket/traceability.md) | ticket — commits and PRs on the item, closing comments, hours that are never invented |
| [azure-devops](ticket/adapters/azure-devops.md) · [jira](ticket/adapters/jira.md) · [linear](ticket/adapters/linear.md) · [local](ticket/adapters/local.md) | ticket — one adapter per tool |
| [theory](backlog/theory.md) | backlog — the principles every finding cites, from story mapping, flow and SRE |
| [story-map](backlog/story-map.md) · [slicing](backlog/slicing.md) · [splitting](backlog/splitting.md) · [workshop](backlog/workshop.md) · [opportunity](backlog/opportunity.md) | backlog — map and refine modes |
| [ordering](backlog/ordering.md) · [flow](backlog/flow.md) · [health-checks](backlog/health-checks.md) · [scoring](backlog/scoring.md) | backlog — order and health modes |

## Measured

`post-mortem` has an eval fixture and a scored assertion set in [`../evals/`](../../evals/README.md): a git repository whose triggering commit sits nine days before the outage window, plus four documents that contradict each other on detection time — one of which blames a named engineer and demands specific remediation. Submitting that incident report verbatim as the answer scores **3/10** on the assertions that test what this skill instructs. **First run (n=1): 1.00 against 0.60 for no skill. Re-run after the SRE book update (2026-11-09, n=3): 1.00 against 0.70.**

`hotfix` (evals 8–11: a Node service, a JVM service with no build tool, a Python script with no tests, and an outage it must route out) and `incident-fix` (evals 12–14: a containerized web app with feature flags, a batch job that corrupted rows, a library with no deploy step) have fixtures and assertions; both assertion sets separate a reference answer from a do-nothing one. **First runs:** hotfix 1.00, 1.00, 1.00 and 0.83 (n=3) against 0.00–0.71 for no skill; incident-fix 0.95 (n=3), 0.90 (n=3) and 1.00 against 0.43–0.60. Each slip was a safety rule — hotfix wrote an incident log during an outage, incident-fix edited code before containment and once kept its count query in a side file — so those rules became hard gates, checked before any other action. **Re-run n=3 each (2026-11-03): 1.00 on all seven** against 0.00–0.71 for no skill. **Re-run again after the SRE book update (2026-11-09, n=3): 1.00 on all seven** against 0.00–0.71.

`release-notes` has one too (eval 29): a tagged git history whose range hides a one-line breaking change, a feature shipped and reverted inside the release, a CVE fix among routine dependency bumps, an improvement nobody measured, internal class and ticket names in the commit subjects, and work committed after the tag. Reference, do-nothing and plausible-but-wrong controls separate as intended (`python3 evals/controls/make_controls.py --only 29`). **First run (n=1): 1.00 against 0.54 for no skill. Re-run (2026-11-05, n=3): 0.90 against 0.39.** Two of three runs left the dropped count and the 18-commit range out of the handoff. The skill now defines the count, puts the range in the handoff template and checks both in its stopping rule: **1.00 against 0.54** (2026-11-09, n=3).
