#!/usr/bin/env bash
# Build the nexus-merge fixture (eval 73): Harbor Bikes' main checkout in repo/ (main at the merge
# of #29), four session worktrees in wt/ (quote-cli, late-fee, receipt, waiver), each with its own
# git-ignored .workflow/ brief and ledger, and the nexus's shared notes in repo/.workflow/nexus/ as
# its last turn left them, 2026-11-19 11:00, plus what the sessions wrote by 11:20.
# The worktrees use relative paths (git 2.48 or later), so a copy of this folder is a working copy.
# Idempotent and deterministic: removes and rebuilds repo/ and wt/ each time.
#
# It deletes repo/ and wt/, so it refuses to run unless evals/setup.sh (or you, on purpose) sets
# EVALS_FIXTURE_BUILD=1: a copy of this folder is what a run works in.
set -euo pipefail
[ "${EVALS_FIXTURE_BUILD:-}" = 1 ] || { echo "make-history.sh: builds an eval fixture; run evals/setup.sh" >&2; exit 1; }
cd "$(dirname "$0")"
case "$(git worktree add -h 2>&1 || true)" in *relative-paths*) ;; *)
  echo "make-history.sh: needs git 2.48 or later (git worktree add --relative-paths)" >&2; exit 1 ;; esac
rm -rf repo wt scripts/.calls.log && mkdir repo wt && cd repo

git init -q -b main
git config user.email "fixture@example.invalid"
git config user.name "Fixture"
git config commit.gpgsign false
git config tag.gpgsign false

python3 -I - <<'PY'
import hashlib
import json
import os
import pathlib
import subprocess
import textwrap

ROOT = pathlib.Path.cwd()
WT = ROOT.parent / "wt"


def write(path, text, root=ROOT):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).lstrip("\n"))


def git(*args, cwd=ROOT, env=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env=dict(os.environ, **(env or {}))).stdout.strip()


def who(when, author):
    email = author.lower().replace(" ", ".") + "@example.invalid"
    return dict(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when, GIT_AUTHOR_NAME=author,
                GIT_COMMITTER_NAME=author, GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_EMAIL=email)


def commit(when, author, subject, cwd=ROOT):
    git("add", "-A", cwd=cwd)
    git("commit", "-q", "-m", subject, cwd=cwd, env=who(when, author))
    return git("rev-parse", "HEAD", cwd=cwd)


def edit(path, old, new, root=ROOT):
    p = root / path
    text = p.read_text()
    assert old in text, (path, old)
    p.write_text(text.replace(old, new))


# ---------------------------------------------------------------- main: the counter app

write(".gitignore", """
.workflow/
__pycache__/
""")
write("README.md", """
# Harbor Bikes — counter software

Rentals, prices and receipts for the harbour bike shop's counter. Python 3.11+, standard library only.

## Running it

    python3 -m fleet.cli quote --hours 3

## Tests

    python3 -m unittest discover -s tests -v

## Merging

Pull requests merge into `main` on the forge, with a merge commit, once CI is green. Nobody pushes to `main`.
""")
write("fleet/__init__.py", "")
write("fleet/pricing.py", '''
"""Rental prices, in cents."""

HOUR_RATE = 600
DAY_RATE = 3000
WEEKEND_DAY_RATE = 3600


def rental_price(hours, weekend=False):
    """The price of a rental of `hours` started hours: hourly, capped at the day rate for each day."""
    if hours <= 0:
        raise ValueError("hours must be positive")
    day = WEEKEND_DAY_RATE if weekend else DAY_RATE
    full_days, rest = divmod(hours, 24)
    return full_days * day + min(rest * HOUR_RATE, day)
''')
write("fleet/rentals.py", '''
"""A rental: which bike, who has it, and when it is due back."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Rental:
    bike_id: str
    customer: str
    start: datetime
    due: datetime
    returned: Optional[datetime] = None

    def is_open(self):
        return self.returned is None

    def hours_booked(self):
        seconds = int((self.due - self.start).total_seconds())
        return max(1, -(-seconds // 3600))
''')
write("fleet/receipt.py", '''
"""The counter receipt, one line per charge."""
from .pricing import rental_price


def euros(cents):
    return f"EUR {cents // 100}.{cents % 100:02d}"


def receipt_lines(rental, weekend=False):
    lines = [
        f"Bike {rental.bike_id} - {rental.customer}",
        f"Out: {rental.start:%Y-%m-%d %H:%M}",
        f"Due: {rental.due:%Y-%m-%d %H:%M}",
    ]
    hours = rental.hours_booked()
    lines.append(f"Rental ({hours} h): {euros(rental_price(hours, weekend))}")
    return lines
''')
write("tests/test_pricing.py", '''
import unittest

from fleet.pricing import DAY_RATE, HOUR_RATE, WEEKEND_DAY_RATE, rental_price


class PricingTest(unittest.TestCase):
    def test_one_hour(self):
        self.assertEqual(rental_price(1), HOUR_RATE)

    def test_hours_capped_at_day_rate(self):
        self.assertEqual(rental_price(10), DAY_RATE)

    def test_two_days(self):
        self.assertEqual(rental_price(48), 2 * DAY_RATE)

    def test_rejects_zero_hours(self):
        with self.assertRaises(ValueError):
            rental_price(0)

    def test_weekend_day_rate(self):
        self.assertEqual(rental_price(24, weekend=True), WEEKEND_DAY_RATE)
''')
write("tests/test_rentals.py", '''
import unittest
from datetime import datetime

from fleet.rentals import Rental

T0 = datetime(2026, 11, 2, 9, 0)


class RentalTest(unittest.TestCase):
    def test_open_until_returned(self):
        r = Rental("B7", "Ines", T0, T0.replace(hour=12))
        self.assertTrue(r.is_open())
        r.returned = T0.replace(hour=11)
        self.assertFalse(r.is_open())

    def test_hours_booked_rounds_up(self):
        self.assertEqual(Rental("B7", "Ines", T0, T0.replace(hour=11, minute=10)).hours_booked(), 3)

    def test_hours_booked_at_least_one(self):
        self.assertEqual(Rental("B7", "Ines", T0, T0).hours_booked(), 1)
''')
write("tests/test_receipt.py", '''
import unittest
from datetime import datetime

from fleet.receipt import euros, receipt_lines
from fleet.rentals import Rental

T0 = datetime(2026, 11, 2, 9, 0)


class ReceiptTest(unittest.TestCase):
    def test_euros_pads_cents(self):
        self.assertEqual(euros(1205), "EUR 12.05")

    def test_lines_name_bike_and_due(self):
        lines = receipt_lines(Rental("B7", "Ines", T0, T0.replace(hour=12)))
        self.assertEqual(lines[0], "Bike B7 - Ines")
        self.assertEqual(lines[2], "Due: 2026-11-02 12:00")

    def test_rental_line_priced(self):
        lines = receipt_lines(Rental("B7", "Ines", T0, T0.replace(hour=12)))
        self.assertEqual(lines[-1], "Rental (3 h): EUR 18.00")

    @unittest.skip("needs the counter printer")
    def test_prints_on_counter_printer(self):
        pass
''')
commit("2026-10-05T10:00:00+02:00", "Lena Brandt", "Harbor Bikes counter: prices, rentals, receipts")
write(".github/workflows/ci.yml", """
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: lint
        run: python3 -m compileall -q fleet tests
      - name: unit tests
        run: python3 -m unittest discover -s tests -v
      - name: smoke
        run: python3 -m fleet.cli quote --hours 3
""")
C2 = commit("2026-10-20T15:30:00+02:00", "Tomas Ek", "ci: lint, unit tests and a smoke quote")

# ---------------------------------------------------------------- #29 quote-cli, merged 2026-11-18

git("switch", "-q", "-c", "quote-cli")
write("fleet/cli.py", '''
"""Counter commands: python3 -m fleet.cli quote --hours N [--weekend]"""
import argparse

from .pricing import rental_price
from .receipt import euros


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fleet")
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("quote", help="price a rental")
    q.add_argument("--hours", type=int, required=True)
    q.add_argument("--weekend", action="store_true")
    a = ap.parse_args(argv)
    print(euros(rental_price(a.hours, a.weekend)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''')
write("tests/test_cli.py", '''
import contextlib
import io
import unittest

from fleet.cli import main


class CliTest(unittest.TestCase):
    def test_quote_prints_euros(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(["quote", "--hours", "3"])
        self.assertEqual(out.getvalue().strip(), "EUR 18.00")
''')
Q1 = commit("2026-11-17T14:00:00+01:00", "Sam Ortiz", "cli: quote command")
git("switch", "-q", "main")
git("merge", "-q", "--no-ff", "-m", "Merge pull request #29 from harbor/quote-cli", "-m", "feat: counter quote command",
    "quote-cli", env={**who("2026-11-18T16:05:00+01:00", "GitHub"), "GIT_COMMITTER_EMAIL": "noreply@github.invalid",
                      "GIT_AUTHOR_EMAIL": "noreply@github.invalid"})
M1 = git("rev-parse", "main")

# ---------------------------------------------------------------- #31 late-fee

git("switch", "-q", "-c", "late-fee", "main")
edit("fleet/rentals.py", "    due: datetime\n", "    due_at: datetime\n")
edit("fleet/rentals.py", "(self.due - self.start)", "(self.due_at - self.start)")
edit("fleet/receipt.py", "{rental.due:%Y-%m-%d %H:%M}", "{rental.due_at:%Y-%m-%d %H:%M}")
L1 = commit("2026-11-19T09:10:00+01:00", "Sam Ortiz", "rentals: rename due to due_at")
write("fleet/late_fee.py", '''
"""The late fee for a rental brought back after its due time (design decisions 1 and 2)."""
from .pricing import DAY_RATE, HOUR_RATE


def hours_late(rental, returned_at):
    seconds = int((returned_at - rental.due_at).total_seconds())
    return max(0, -(-seconds // 3600))


def late_fee_cents(rental, returned_at):
    return min(hours_late(rental, returned_at) * HOUR_RATE, DAY_RATE)
''')
write("tests/test_late_fee.py", '''
import unittest
from datetime import datetime, timedelta

from fleet.late_fee import late_fee_cents
from fleet.pricing import DAY_RATE, HOUR_RATE
from fleet.rentals import Rental

DUE = datetime(2026, 11, 2, 12, 0)
RENTAL = Rental("B7", "Ines", DUE - timedelta(hours=3), DUE)


class LateFeeTest(unittest.TestCase):
    def test_on_time_costs_nothing(self):
        self.assertEqual(late_fee_cents(RENTAL, DUE), 0)

    def test_charges_each_started_hour(self):
        self.assertEqual(late_fee_cents(RENTAL, DUE + timedelta(minutes=10)), HOUR_RATE)

    def test_two_hours_late(self):
        self.assertEqual(late_fee_cents(RENTAL, DUE + timedelta(hours=2)), 2 * HOUR_RATE)

    def test_capped_at_day_rate(self):
        self.assertEqual(late_fee_cents(RENTAL, DUE + timedelta(hours=9)), DAY_RATE)
''')
L2 = commit("2026-11-19T09:40:00+01:00", "Sam Ortiz", "late fee per started hour, capped at the day rate")

# ---------------------------------------------------------------- #32 receipt

git("switch", "-q", "-c", "receipt", M1)
p = ROOT / "fleet/receipt.py"
p.write_text(p.read_text() + textwrap.dedent('''


def return_lines(rental, fee_cents):
    """The return block: when the bike came back, how late, and the late fee as a line of its own.
    The fee is passed in, never computed here (DEC-2)."""
    seconds = max(0, int((rental.returned - rental.due).total_seconds()))
    hours = -(-seconds // 3600)
    lines = [f"Returned: {rental.returned:%Y-%m-%d %H:%M}"]
    if hours:
        lines.append(f"Late by {hours} h")
        lines.append(f"Late fee: {euros(fee_cents)}")
    return lines
'''))
write("tests/test_receipt_returns.py", '''
import unittest
from datetime import datetime, timedelta

from fleet.receipt import return_lines
from fleet.rentals import Rental

DUE = datetime(2026, 11, 2, 12, 0)


class ReturnLinesTest(unittest.TestCase):
    def test_late_fee_is_its_own_line(self):
        r = Rental("B7", "Ines", DUE - timedelta(hours=3), DUE, returned=DUE + timedelta(hours=2))
        self.assertEqual(return_lines(r, 1200), ["Returned: 2026-11-02 14:00", "Late by 2 h", "Late fee: EUR 12.00"])

    def test_on_time_has_no_fee_line(self):
        r = Rental("B7", "Ines", DUE - timedelta(hours=3), DUE, returned=DUE)
        self.assertEqual(return_lines(r, 0), ["Returned: 2026-11-02 12:00"])
''')
R1 = commit("2026-11-19T09:35:00+01:00", "Ada Moreau", "receipt: the late fee as a line of its own")

# ---------------------------------------------------------------- waiver (no PR yet)

git("switch", "-q", "-c", "waiver", M1)
write("fleet/waiver.py", '''
"""Staff waivers for late fees (design decision 4: one audit line each)."""


def waive(fee_cents, reason, staff):
    if not reason or not reason.strip():
        raise ValueError("a waiver needs a reason")
    return {"waived_cents": fee_cents, "reason": reason.strip(), "by": staff}
''')
write("tests/test_waiver.py", '''
import unittest

from fleet.waiver import waive


class WaiverTest(unittest.TestCase):
    def test_reason_required(self):
        with self.assertRaises(ValueError):
            waive(1200, "  ", "lena")
''')
W1 = commit("2026-11-19T10:05:00+01:00", "Ada Moreau", "waiver: a reason is required")
git("switch", "-q", "main")

# ---------------------------------------------------------------- the worktrees

for slug in ("quote-cli", "late-fee", "receipt", "waiver"):
    git("worktree", "add", "-q", "--relative-paths", f"../wt/{slug}", slug)

BRIEFS = {
    "quote-cli": ("counter quote command", [
        "1. `python3 -m fleet.cli quote --hours N` prints the price of a rental of N hours in euros — verified by tests/test_cli.py::CliTest::test_quote_prints_euros"],
        "None. Approved under DEC-1's limit; no Revisions."),
    "late-fee": ("late fee", [
        "1. A rental returned after its due time costs one hour rate per started hour late — verified by tests/test_late_fee.py::LateFeeTest::test_charges_each_started_hour",
        "2. The fee for one rental is capped at the day rate — verified by tests/test_late_fee.py::LateFeeTest::test_capped_at_day_rate"],
        "2026-11-19 — Rental.due renamed to due_at: the fee reads clearer against returned_at (refactor-review)."),
    "receipt": ("receipt return block", [
        "1. The receipt shows the late fee as a line of its own, with the hours late — verified by tests/test_receipt_returns.py::ReturnLinesTest::test_late_fee_is_its_own_line"],
        "2026-11-18 — the fee is a parameter, not computed here (DEC-2)."),
    "waiver": ("staff waiver", ["1. A waiver needs a reason", "2. Each waiver writes one audit line"], "none"),
}
HEADS = {"quote-cli": Q1, "late-fee": L2, "receipt": R1, "waiver": W1}
for slug, (title, crit, rev) in BRIEFS.items():
    status = "draft — awaiting approval" if slug == "waiver" else "approved"
    write(".workflow/brief.md", f"""
# Brief: {title} ({slug})

**Status:** {status}
**Base:** `{M1[:7] if slug != "quote-cli" else C2[:7]}`

## Acceptance criteria
""" + "\n".join(crit) + f"""

## Revisions
- {rev}
""", root=WT / slug)
    if slug != "waiver":
        write(".workflow/ledger.md", f"""
# Ledger — {slug}

### Smells
- none promoted

### Findings (unadjudicated)
- F1 · minor · {title}: an error message could name the input — `fleet/` (devils-advocate)

### Verdicts
- F1 · CONFIRMED · minor — carried as a tracked follow-up

### Verdict: GO
Head `{HEADS[slug][:7]}`; findings settled; F1 carried.
""", root=WT / slug)
# waiver is mid-slice: one uncommitted change in its worktree
edit("fleet/waiver.py", '    return {"waived_cents"', '    # TODO: write the audit line (slice 2)\n    return {"waived_cents"', root=WT / "waiver")

# ---------------------------------------------------------------- the shared notes, as the last turn left them

NOTES = ROOT / ".workflow/nexus"
s = lambda sha: sha[:7]

write("decisions.md", """
# Decisions — the user's, verbatim

## DEC-1: At most three sessions at once
**Decided:** 2026-11-17 by Nora · **Asked by:** the nexus · **Applies to:** all sessions
**Question:** How many sessions may run at once on this machine?
**Answer:** "Three at most. The laptop fans are already screaming."
**Means:** the nexus starts a fourth only when one is archived.
**Supersedes:** —

## DEC-2: The receipt takes the fee as a number
**Decided:** 2026-11-18 by Nora · **Asked by:** receipt · **Applies to:** receipt, late-fee
**Question:** Should the receipt compute the late fee itself, or be handed it?
**Answer:** "Hand it the number. The fee lives in one place."
**Means:** `return_lines` takes `fee_cents`; only `fleet/late_fee.py` computes a fee.
**Supersedes:** —

## DEC-3: The increment is these six entries
**Decided:** 2026-11-17 by Nora · **Asked by:** the nexus · **Applies to:** all sessions
**Question:** Is increment.json's list (REQ-1–REQ-5, J-1) the increment?
**Answer:** "Yes, that's the increment."
**Means:** increment.json is the definition of done.
**Supersedes:** —
""", root=NOTES)
seal = hashlib.sha256((NOTES / "decisions.md").read_bytes()).hexdigest()[:12]

write("env.md", f"""
# Environment — Harbor Bikes, late returns
**Recorded:** 2026-11-17 09:20 at `{s(C2)}`, baseline re-run 2026-11-18 16:20 at `{s(M1)}` · **Sources:** the CI workflow, README.md

## Commands
- **Test (full):** `python3 -m unittest discover -s tests -v` — from CI
- **Test (focused):** `python3 -m unittest tests.test_<module> -v` won't import (tests/ is not a package): `python3 -m unittest discover -s tests -p 'test_<module>.py' -v`
- **Lint / type-check:** `python3 -m compileall -q fleet tests` — from CI
- **Build:** none
- **Start:** none: a counter CLI
- **Smoke:** `python3 -m fleet.cli quote --hours 3` — prints `EUR 18.00`

## Baseline
- **Suite on `{s(M1)}`:** 12/0/1, under a second
- **Red on the base:** none
- **Smoke on `{s(M1)}`:** passed

## Per session
- nothing to install: standard library only
- **Working files:** the sessions' `.workflow/` is git-ignored in this repo (`.gitignore`: `.workflow/`)
""", root=NOTES)

entries = [
    ("REQ-1", "requirement", "The counter quotes a rental's price from the command line", ["run `python3 -m fleet.cli quote --hours 3`", "see EUR 18.00"], ["quote-cli"],
     {"test": "tests/test_cli.py::CliTest::test_quote_prints_euros", "pr": 29, "base": s(M1), "checked": "2026-11-18"}),
    ("REQ-2", "requirement", "A rental returned after its due time is charged one hour rate per started hour late", ["return a bike 10 minutes late", "see one hour rate charged"], ["late-fee"], None),
    ("REQ-3", "requirement", "The late fee for one rental is capped at one day rate", ["return a bike 9 hours late", "see the day rate, not nine hours"], ["late-fee"], None),
    ("REQ-4", "requirement", "The receipt shows the late fee as a line of its own, with the hours late", ["return a bike 2 hours late", "see 'Late by 2 h' and 'Late fee: EUR 12.00' on the receipt"], ["receipt"], None),
    ("REQ-5", "requirement", "Staff can waive a late fee with a reason, written to the audit log", ["waive a fee without a reason: refused", "waive it with one: one audit line"], ["waiver"], None),
    ("J-1", "journey", "A customer returns two hours late, sees the fee on the receipt, staff waive it, the reprint shows it waived", ["return late", "read the receipt", "waive with a reason", "reprint"], ["waiver"], None),
]
inc = {"increment": "Harbor Bikes, late returns", "design": ".workflow/designs/20261117-0900-late-returns.md", "base": "main",
       "confirmed": "DEC-3", "entries": [
           {"id": i, "kind": k, "description": d, "steps": st, "slices": sl, "passes": ev is not None, "evidence": ev}
           for i, k, d, st, sl, ev in entries]}
(NOTES / "increment.json").write_text(json.dumps(inc, indent=2) + "\n")

write("status.md", f"""
# Nexus — Harbor Bikes, late returns
**Updated:** 2026-11-19 11:00 · **Base:** main at `{s(M1)}` · **Running:** 3 (limit: DEC-1) · **Free disk:** 48 GB
**Register:** DEC-3 · {seal}
**Increment:** 1 of 6 entries passing on the base · 0 dropped · failing again: none

| Session | Parent | Slice or track | PR | Stage | Waiting on | Next |
|---|---|---|---|---|---|---|
| quote-cli | — | counter quote command | #29 merged at `{s(M1)}` | after merge | nexus: confirm clean | archive once it says done |
| late-fee | — | late fee | #31 at `{s(L2)}` | tyr-verdict | user: merge go | merge |
| receipt | — | receipt return block | #32 at `{s(R1)}` | tyr-verdict | user: merge go | merge |
| waiver | — | staff waiver | none yet | tdd | nothing | slice 2: the audit line |

## Waiting on the user
- PR #31 — ready to merge at `{s(L2)}`, integrated with main at `{s(M1)}` (since 2026-11-19 10:50)
- PR #32 — ready to merge at `{s(R1)}`, integrated with main at `{s(M1)}` (since 2026-11-19 10:55)

## Leases
- none

## Archived
- none
""", root=NOTES)

write("resources.md", """
# Resources

## Exclusive resources
| Resource | Holder | Since | Limit | Queue |
|---|---|---|---|---|
| the counter printer (test unit, one) | — | — | — | — |

## Sequence-numbered files
None in this repo.

## Scratch names and ports
| Session | Databases / ports / paths |
|---|---|
| quote-cli | `/tmp/harbor-quote-cli`, port 8061 |
| late-fee | `/tmp/harbor-late-fee`, port 8062 |
| receipt | `/tmp/harbor-receipt`, port 8063 |
| waiver | `/tmp/harbor-waiver`, port 8064, `audit/` under its scratch path |

## Read-only for everyone
- the shop's live till export (production)
""", root=NOTES)
write("findings.md", """
# Cross-slice findings

None open.
""", root=NOTES)
write("labels.md", """
# Label series

| Series | Means | Taken | Next free | Owner |
|---|---|---|---|---|
| S | a difference the user signed off, with counts | none | S1 | the user; the nexus assigns |
""", root=NOTES)
write("owner-checks.md", """
# Owner checks

| # | Check | Why | From | Since | Done |
|---|---|---|---|---|---|
| 1 | The live till prints the new late-fee line in its own column | the till's layout is configured in the shop, not here | receipt | 2026-11-19 | ☐ |
""", root=NOTES)

LOG_HEAD = "# {slug} — {title}\n**Worktree:** {wt} · **Branch:** {slug} · **PR:** {pr} · **Parent:** — · **Scratch:** `/tmp/harbor-{slug}`, port {port}\n"
write("sessions/quote-cli.md", LOG_HEAD.format(slug="quote-cli", title="counter quote command", wt="wt/quote-cli", pr="#29", port=8061) + f"""
## tyr-verdict — 2026-11-18 14:30
GO at `{s(Q1)}`. Suite: 12 passed, 0 failed, 1 skipped. `ledger.py status`: computed verdict: GO; waived: none.
Delivers: REQ-1 → tests/test_cli.py::CliTest::test_quote_prints_euros
Carried: F1 (minor: the error message could name the input), tracked as a follow-up

**Status:** tyr-verdict · waiting
**Waiting on:** nexus: merge
**Next:** none until merged
**Head:** `{s(Q1)}` · **PR:** #29

## From nexus — 2026-11-18 16:10
Merged #29 at `{s(M1)}` on Nora's go. main gained only your files. Confirm your worktree is clean and report done.

## After merge — 2026-11-19 11:20
`git status`: nothing to commit, working tree clean. The branch's head is `{s(Q1)}`, the head that was merged. No stashes. My brief and ledger are in `.workflow/` (git-ignored).

**Status:** done · done
**Waiting on:** nothing
**Next:** nothing — ready to archive
**Head:** `{s(Q1)}` · **PR:** #29 merged
""", root=NOTES)
write("sessions/late-fee.md", LOG_HEAD.format(slug="late-fee", title="late fee", wt="wt/late-fee", pr="#31", port=8062) + f"""
## tdd — 2026-11-19 09:45
Two slices green: `{s(L1)}` renames `Rental.due` to `due_at` (refactor-review promoted it), `{s(L2)}` adds the fee and its cap. Suite: 16 passed, 0 failed, 1 skipped.

## tyr-verdict — 2026-11-19 10:40
GO at `{s(L2)}`. Suite on `{s(L2)}`: 16 passed, 0 failed, 1 skipped. `ledger.py status`: computed verdict: GO; waived: none.
Delivers: REQ-2 → tests/test_late_fee.py::LateFeeTest::test_charges_each_started_hour
Delivers: REQ-3 → tests/test_late_fee.py::LateFeeTest::test_capped_at_day_rate
Carried: F1 (minor: the error message could name the input), tracked as a follow-up

**Status:** tyr-verdict · waiting
**Waiting on:** nexus: merge
**Next:** none until merged
**Head:** `{s(L2)}` · **PR:** #31

## From nexus — 2026-11-19 10:50
Gate passed at `{s(L2)}`, integrated with main at `{s(M1)}`: 16/0/1. With Nora for the go.
""", root=NOTES)
write("sessions/receipt.md", LOG_HEAD.format(slug="receipt", title="receipt return block", wt="wt/receipt", pr="#32", port=8063) + f"""
## tdd — 2026-11-19 09:40
`return_lines` takes the fee as a number (DEC-2). Suite: 14 passed, 0 failed, 1 skipped.
Owner check: the live till prints the new line in its own column (filed as #1).

## tyr-verdict — 2026-11-19 10:45
GO at `{s(R1)}`. Suite on `{s(R1)}`: 14 passed, 0 failed, 1 skipped. `ledger.py status`: computed verdict: GO; waived: none.
Delivers: REQ-4 → tests/test_receipt_returns.py::ReturnLinesTest::test_late_fee_is_its_own_line
Carried: F1 (minor: the error message could name the input), tracked as a follow-up

**Status:** tyr-verdict · waiting
**Waiting on:** nexus: merge
**Next:** none until merged
**Head:** `{s(R1)}` · **PR:** #32

## From nexus — 2026-11-19 10:55
Gate passed at `{s(R1)}`, integrated with main at `{s(M1)}`: 14/0/1. With Nora for the go.
""", root=NOTES)
write("sessions/waiver.md", LOG_HEAD.format(slug="waiver", title="staff waiver", wt="wt/waiver", pr="none yet", port=8064) + f"""
## tdd — 2026-11-19 10:05
Slice 1 green at `{s(W1)}`: a waiver needs a reason. Suite: 13 passed, 0 failed, 1 skipped.
Brief still a draft: sent for approval as Q-waiver-1 on 2026-11-18; building slice 1 meanwhile, as the contract allows.

**Status:** tdd · working
**Waiting on:** nothing
**Next:** slice 2, the audit line (expect it by 12:30)
**Head:** `{s(W1)}` · **PR:** none yet
""", root=NOTES)
write("designs/20261117-0900-late-returns.md", """
# Design: late returns

**Status:** resolved
**Date:** 2026-11-17

Slices, in merge order: quote-cli, late-fee, receipt, waiver. See increment.json for the entries each delivers.
""", root=ROOT / ".workflow")

# eval 73's prompt names these two: a change to anything above changes them, and the prompt with them
assert (M1[:7], L2[:7]) == ("a8961c7", "253222c"), f"main {M1[:7]}, late-fee {L2[:7]}: update eval 73's prompt"
print("M1", M1)
print("L2", L2)
print("R1", R1)
print("Q1", Q1)
print("W1", W1)
print("seal", seal)
PY

echo "nexus-merge: main at $(git rev-parse --short main); worktrees: $(git worktree list | wc -l | tr -d ' ')"
