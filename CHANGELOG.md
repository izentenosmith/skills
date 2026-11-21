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

[Unreleased]: https://github.com/izentenosmith/skills/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/izentenosmith/skills/releases/tag/v1.0.0
