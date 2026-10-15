# harness — the closing loop, run by code

The `development` skills describe a loop with hard rules: the teardown never runs the suite, every finding is adjudicated, a refuted finding stays refuted, an INCONCLUSIVE goes back for evidence once, three iterations at most, and the verdict follows from what's still open. In the skills those rules are prose that the agent is asked to follow — the model is both the worker and the referee.

This folder makes the referee a program. The model still does every judgment; the harness owns everything that isn't judgment.

```
                       ┌──────────── iteration n (≤ 3) ─────────────┐
 tdd (stages 1–3,  ──► │ refactor-review → devils-advocate → tyr    │ ──► GO        exit 0
 by hand, as now)      │      gate          3–9 read-only    verdict│ ──► ESCALATED exit 3
                       │    green/green     delegates + rank  + one │
                       │                    verifier per finding    │
                       └───────────── NO-GO: tdd on the slices ─────┘
```

| File | What it is |
|---|---|
| [`loop.py`](loop.py) | The orchestrator. Drives stages 4–6 and the loop back through tdd with headless `claude -p` calls. |
| [`ledger.py`](ledger.py) | The ledger's grammar as code: parser, checker, verdict arithmetic, and the only writer `loop.py` uses. Works on its own against a ledger the skills wrote by hand. |
| [`LEDGER.md`](LEDGER.md) | The grammar and the rules, for people. |
| [`redgreen.py`](redgreen.py) | Proves new tests were **red on the pre-fix code** and are green with the fix, for any language. `loop.py` uses it before closing a remediation slice; hotfix, tdd and incident-fix can call it directly. |
| [`incident.py`](incident.py) | The incident-fix log: entries stamped from the system clock, production actions refused without their own confirmation, a closing gate on contributing factors, and a timeline for the post-mortem. |
| [`tests/`](tests) | `python3 -m unittest discover harness/tests` — the grammar, the rules, and the whole loop against a stub `claude`. |

Stdlib Python 3.10+, no dependencies. The skills don't need any of this — every skill folder still works copied on its own, in Cursor or Claude Code. The harness is an optional layer that enforces what they ask for when you want it enforced.

## What moved from prose into code

| Rule the skills state | Who enforces it now |
|---|---|
| devils-advocate fans out by attack surface, never below three delegates, all at once | `loop.py` dispatches 3 grouped delegates (9 on a diff over 400 changed lines) in parallel |
| The teardown **does not execute** — no suite, no test, no mutation | Delegates get `--tools Read,Grep,Glob`. They *can't* run anything, rather than being asked not to |
| A delegate that never returns is an **unattacked surface**, not a clean one | Recorded under `### Surfaces` by the harness |
| tyr verifies each finding with a reproduction; verifiers don't fix | One verifier per finding, each in a throwaway copy of the repo |
| Collect every verifier before judging | `fan_out` waits on all of them; tyr's call is made once, on the whole slate |
| The suite is green before and after refactor-review, and after tdd | `--test-cmd` is run as a gate; red stops the loop (exit 4) |
| The ledger is append-only and only the running stage writes it | Agents never write it. The harness snapshots it, restores it if an agent edits it anyway, and appends through `ledger.render_*` |
| Every CONFIRMED gets a slice; REFUTED carries *Reopens only if*; INCONCLUSIVE carries what settles it | Validated on tyr's answer; one correction round, then the harness stops |
| A slice closes when its test exists | The tests tdd added are run against a snapshot of the pre-fix code (`redgreen.py`): if they pass there, they don't capture the defect and **no slice closes**. Each test name tdd reports must also be found in the repo |
| Every carried smell is re-examined each pass | Missing decisions are recorded as "left, not re-examined" and logged |
| GO / NO-GO / ESCALATED, the three-iteration cap, the stall rule, one re-run per INCONCLUSIVE | `ledger.judge()` computes it. tyr states a verdict too; if they disagree the ledger records both and the computed one stands |

What stays with the model: which smells to fix, what's a defect, how severe, whether evidence holds, what each slice must make true. What stays with you: stages 1–3, and any ESCALATED decision.

## Running it

From a repo where stage 3 (tdd) has finished and the suite is green:

```bash
python3 path/to/skills/harness/loop.py --repo . --test-cmd ".venv/bin/python -m pytest -q"
```

The first run remembers `--test-cmd` and `--base` in `.workflow/harness.json`, so later runs are just `--repo .`. The **ledger is the state**: stop it any time — Ctrl-C, a red gate, a crash — and the next run picks up at the first stage the ledger doesn't show as done.

| Flag | Default | |
|---|---|---|
| `--base` | merge-base with `main` | what the diff is measured against; `HEAD` when you're on the base branch itself |
| `--skills` | `../skills` next to this folder | where the `SKILL.md` folders are; the repo's `.claude/skills` is searched too |
| `--model`, `--delegate-model` | your Claude default | e.g. a stronger model for the stages that judge or write code, a cheaper one for delegates |
| `--concurrency` | 4 | parallel delegate calls |
| `--budget-usd` | none | spend cap per `claude` call |
| `--cap` | 3 | iterations |
| `--once` | | run one stage and stop — to watch it step by step |
| `--dry-run` | | write the next stage's prompts to `.workflow/runs/…/calls/` and call nothing |

Each run leaves its prompts, raw model output and the diff each teardown saw in `.workflow/runs/<timestamp>/`. Ignore `.workflow/runs/` in the host repo; `ledger.md`, `brief.md` and `harness.json` are worth keeping if you commit `.workflow/` at all.

### When it stops

- **GO** (exit 0) — nothing open. Minors ship as tracked follow-ups, carried smells are named in the verdict's reason.
- **ESCALATED** (exit 3) — the decision has left the loop. Read the last `### Verdict` reason, then either fix by hand, take it back to agent-brief / architect-deep-dive, or accept the risk: append to the last iteration

  ```markdown
  ### Decisions
  - **F4** — waived: <why you accept it>
  ```

  and run `ledger.py check` — a waived finding stops counting as open.
- **Gate failed** (exit 4) — the suite was red where it had to be green. Nothing was recorded for that stage, so fixing the suite and re-running resumes at the same stage.
- **Error** (exit 1) — a malformed answer that survived its correction round, an unreadable ledger, a timeout. The message names it; the call's prompt and output are in the run folder.

### Without the orchestrator

The checker is useful on its own, against a ledger the skills wrote by hand:

```bash
python3 harness/ledger.py check  .workflow/ledger.md            # grammar + every loop rule
python3 harness/ledger.py check  .workflow/ledger.md --against old-ledger.md   # + append-only
python3 harness/ledger.py status .workflow/ledger.md            # computed verdict, what's open, next stage
```

### Proving a test red — `redgreen.py`

A test written alongside its fix can pass for the wrong reason. The only proof it captures the bug is running it against the code without the fix:

```bash
python3 harness/redgreen.py check --repo . --cmd "<test command>"            # test + fix uncommitted, base = HEAD
python3 harness/redgreen.py check --repo . --cmd "<cmd>" --base HEAD~1       # fix already committed
python3 harness/redgreen.py snapshot --repo .                                # pin "before" when the tree is already dirty
python3 harness/redgreen.py check --repo . --cmd "pytest {tests}" --expect "AssertionError"   # focused, and failing for the right reason
```

It checks out the base in a temporary worktree, copies in only the test files that changed (found by path shape across ecosystems, or given with `--tests`), runs the command there — it must **fail** — and runs it again in your tree, where it must **pass**. Your index and working tree are never touched. Verdicts: `red-green`, `not-red` (the test passes without the fix), `not-green`, `wrong-reason` (failed, but not matching `--expect`), `no-tests`.

### Keeping the incident log — `incident.py`

```bash
python3 harness/incident.py new docs/incidents/2026-10-15-checkout.md --title "checkout 5xx" --severity SEV2 \
    --why "30% of checkouts failing" --detected-by "alert — checkout-5xx-rate"
python3 harness/incident.py log  <log> proposed "disable flag new-pricing — undo in 30 s"
python3 harness/incident.py log  <log> confirmed "user approved: disable new-pricing"
python3 harness/incident.py log  <log> "action[prod]" "ops/flags set new-pricing off"
python3 harness/incident.py log  <log> impact-start "first 5xx in the logs" --at 2026-10-15T14:07:02Z
python3 harness/incident.py factor <log> "no canary for flag rollouts" --follow-up "flag rollouts start at 1%" --owner platform --due 2026-11-01
python3 harness/incident.py check <log>
python3 harness/incident.py timeline <log>      # the post-mortem's spine, with time to detect / mitigate / resolve
```

Every time comes from the system clock except backfilled `impact-start` and `change` entries. `log` **refuses** a production action with no `confirmed` entry of its own since the last one, and refuses `closed` while any contributing factor lacks an owner and date or an accepted-risk reason — or while a human-detected incident has no follow-up for the missing alert. The format is the one in the incident-fix skill's `incident-log.md`, so a log written by hand checks the same way.

## Trade-offs worth knowing

- **It's Claude Code only.** The skills stay portable; this layer drives `claude -p`. Calls run with `--strict-mcp-config --setting-sources project --disable-slash-commands`, so your user-level hooks, plugins and MCP servers don't load into them — that's what keeps each call's context (and bill) small.
- **Write stages and verifiers run with `acceptEdits` and Bash.** tdd and refactor-review edit your working tree, as they would by hand. Verifiers work in a copy under your temp dir, with `.venv` / `node_modules` symlinked back rather than copied.
- **The harness can't make a judgment better** — only make sure it happens, on the right inputs, and is recorded in a shape the next stage can trust.
- **Stages 1–3 are not in the loop.** architect-deep-dive is a conversation with you; tdd's first pass is the build itself. The harness starts at stage 4, and only re-enters tdd for remediation slices.
