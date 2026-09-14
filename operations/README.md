# operations

Two skills for a system that is already running and already shipped. They share nothing but an audience outside the code, and neither depends on the other.

## The skills

| Skill | What it does |
|-------|--------------|
| [release-notes](release-notes/SKILL.md) | Reads the change set from git, classifies every change (including an explicit **drop** bucket for anything with no user-visible effect), and translates each survivor from what was built into what the reader can now do. Depth matched to scope; breaking changes above the fold. |
| [post-mortem](post-mortem/SKILL.md) | Reconstructs a **resolved** incident into a blameless written record — timeline built from a git history date range plus incident docs and PDFs, quantified impact, and contributing factors rather than a single root cause. |

## How to use them

**Copy the folder you want into the repo you're working in**, alongside wherever that repo keeps its agent skills. Each folder is self-contained — `SKILL.md` plus its reference docs — so one folder is a complete install of one skill.

Then either let the agent trigger the skill when your request matches its `description`, or call it by name:

```
/release-notes   /post-mortem
```

**`post-mortem` takes inputs you have to supply**: a date range for the git history (`2026-08-03 12:00 UTC → 2026-08-04 10:00 UTC`) and whatever incident documentation exists — the incident report, a vendor PDF, a chat export, alert emails, monitoring screenshots. It reconstructs from those; it cannot reconstruct from a description of the incident alone.

`release-notes` takes a range too, usually a tag pair (`v2.3.0..v2.4.0`) or a date window.

## What they have in common

**Both are written for someone who is not reading your code**, and both are therefore mostly exercises in translation and in deciding what to leave out.

- `release-notes` translates commits into user outcomes, and **drops everything with no user-visible effect**. The drop bucket is the load-bearing part: every dropped entry is attention returned to the entries that matter, and a note listing a lint fix beside a new feature teaches readers the document is noise.
- `post-mortem` translates artifacts into a timeline, and **stops at describing**. It does not propose remediation, assign work, or recommend what to build — the incident is solved, and a document that reconstructs *and* prescribes has an incentive to shape the reconstruction toward the prescription.

Both also publish under a deadline rather than at completeness. Release notes are read in the days after a release and almost never after; a postmortem circulated in three days with two open questions beats a complete one in three weeks, because memories decay fast and log retention decays faster.

## Reference docs

| Doc | Used by |
|-----|---------|
| [anatomy](release-notes/anatomy.md) | release-notes — the six elements, the commit→outcome translation rules, a full template |
| [distribution](release-notes/distribution.md) | release-notes — depth to scope, when visuals earn their place, where to publish |
| [evidence-sources](post-mortem/evidence-sources.md) | post-mortem — reading a git range, incident PDFs, chat exports and monitoring into a sourced timeline |
| [blameless-culture](post-mortem/blameless-culture.md) | post-mortem — why blameless is a data-collection strategy, and the language patterns that break it |
| [contributing-factors](post-mortem/contributing-factors.md) | post-mortem — past single-root-cause; the categories to sweep and where to stop descending |

## Measured, partly

`post-mortem` has an eval fixture and a scored assertion set in [`../evals/`](../evals/README.md): a git repository whose triggering commit sits nine days before the outage window, plus four documents that contradict each other on detection time — one of which blames a named engineer and demands specific remediation. Submitting that incident report verbatim as the answer scores **3/10** on the assertions that test what this skill instructs. **No with-skill run has been scored yet**, so there is no number for the skill itself.

`release-notes` has no eval.
