# Changelog

Every notable change to this repository is recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Each release is a git tag `vX.Y.Z` on
`main`; see [How to pin an install](README.md#pinning-a-version) and
[how a release is cut](.github/RELEASING.md).

## What the version number means

One version covers the whole repository: every skill, the harness and the evals.

- **Major** — something an existing install or a later stage stops understanding:
  - a skill renamed or removed (`npx skills add … --skill <name>` stops finding it);
  - a changed output format or grammar that a later stage or the harness parses, such as the
    brief's sections and criterion → test mapping, the ledger grammar in `ledger-format.md`, or a
    report's file name or required headings;
  - a removed install path (an install command, or a folder layout the README tells you to copy).
- **Minor** — something new that leaves the existing behaviour working: a new skill, a new eval, a
  new mode of an existing skill, a new harness.
- **Patch** — wording, fixes to a skill's instructions that don't change what it writes, grader
  and checker fixes, documentation.

## [Unreleased]

### Added

- **A size budget for every SKILL.md body**: 375 lines and 3,700 words (frontmatter excluded,
  reference files not counted), checked by `check_repo.py` through `.github/scripts/budget.py`.
  peer-review, pr-prep, architect-deep-dive, dockerfile and tdd are over it and have dated
  allowances that end 2027-02-28.
- **[SCOPE.md](SCOPE.md)** sets what gets in: a failure seen in a real session, and no new skill
  where existing ones compose. **[.out-of-scope/](.out-of-scope/README.md)** records the ideas
  taken out and why.
- **A deterministic routing check in CI** (`.github/scripts/routing.py`, stdlib BM25 with a Porter
  stemmer, no model): every should-trigger case in `evals/trigger/cases.json` must rank its skill
  within the top 6 of 43, no near-miss may rank the skill under test first, and no two descriptions
  may pass TF-IDF cosine 0.40. Twelve current misses are listed as known failures that may only
  shrink. `--report` prints the distributions the thresholds come from.
- **Trigger cases for the 18 skills that had none**, three should-trigger and three near-miss each,
  so all 43 skills are covered: 258 cases, 172 train and 86 held out (seed 20261124).

### Changed

- **Skill descriptions are capped at 500 characters**, checked in CI for every family
  (`authoring.DESCRIPTION_BUDGET`, measured on the parsed YAML value). The 30 descriptions over it
  were rewritten to open with a verb and keep one trigger per mode and their routing to
  neighbouring skills: 31,263 → 19,873 characters across the 43 skills (average 727 → 462).
  On the trigger eval (Opus, 450 runs each side) no skill lost a hit or gained a false trigger:
  should-trigger 219/225 → 223/225, false triggers 0/225 both times.

## [1.0.0] - 2026-11-21

The first tagged release: what had built up on `main` since the repo started in June 2026.

### Added

- **Forty-three skills in nine families**, each a self-contained folder with a `SKILL.md`, its
  reference docs and any checker it runs:
  - **development** — the seven-stage pipeline `architect-deep-dive` → `agent-brief` →
    `acceptance-tests` → `tdd` → `refactor-review` → `devils-advocate` → `tyr-verdict`, and
    `nexus` to coordinate several pipelines at once. The brief and the ledger have a fixed grammar,
    checked by the bundled `brief.py`, `ledger.py` and `redgreen.py`.
  - **containers** — `dockerfile`, `docker-compose`, `container-hardening`, `container-debug`,
    `docker-swarm`.
  - **operations** — `hotfix`, `incident-fix`, `post-mortem`, `release-notes`, `ticket`,
    `backlog`.
  - **database** — `dbarchitect`, `dbaudit`, `dbdesign`, `dbdiagram`, `dbpropose`, `dbbuild`,
    `dbquery`.
  - **networking** — `netaudit`, `netdesign`, `netdiagram`, `netpropose`, `netblueprint`.
  - **infrastructure** — `terraform`, `pipelines` (review, design and propose modes).
  - **security** — `threatmodel`, `appsec`, `hardening` (review, design and propose modes).
  - **review** — `pr-prep`, `code-xray`, `peer-review`, `test-review`, `concurrency-review`,
    `review-retro`.
  - **memory** — `repo-memory` (install, capture, dream and audit modes).
- **The harness** ([`harness/`](harness/README.md)), the skills' rules run as code through headless
  `claude -p`: `pipeline.py` and `loop.py` for the development pipeline and its closing loop,
  `fix.py` (bug → pull request), `postmortem.py`, `dbworkflow.py` / `dbreview.py`,
  `networkflow.py` / `netreview.py`, and `prreview.py` (one pull request through every review
  skill). It needs a clone; `npx skills add` installs skills only.
- **The evals** ([`evals/`](evals/README.md)): 64 evals (0–63) with seeded fixtures, capability
  and delta assertions, controls that must separate, and the recorded benchmark in
  [`evals/benchmark.md`](evals/benchmark.md). Eval 59 is held out as a test set.
- **CI** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)), calling no model: skill
  frontmatter, no symlinks under `skills/`, shared copies in sync with their sources, every
  relative link, eval wiring and eval health, `actionlint`, a `.memory/` audit, the harness tests on
  Python 3.13 and 3.14, and every eval control. `main` is protected by a ruleset that requires a
  pull request with the four CI checks green.
- **Install by name** with the `skills` CLI (`npx skills add izentenosmith/skills --skill <name>`),
  or by copying a skill folder.
- **Install as a Claude Code plugin**: `.claude-plugin/` makes the repo a marketplace,
  `izentenosmith`, offering every skill as one plugin, `izentenosmith-skills`, at version 1.0.0. The plugin is
  `skills/` alone; `harness/` and `evals/` are not installed
  (`claude plugin marketplace add izentenosmith/skills`, then
  `claude plugin install izentenosmith-skills@izentenosmith`). `check_repo.py` fails when the
  plugin's version differs from the top release here, when its family list misses a family, or when
  its source widens past `skills/`.

[Unreleased]: https://github.com/izentenosmith/skills/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/izentenosmith/skills/releases/tag/v1.0.0
