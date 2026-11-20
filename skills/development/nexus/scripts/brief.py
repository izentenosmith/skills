#!/usr/bin/env python3
"""Check a .workflow/brief.md against what the development skills promise about it.

The brief is the build plan agent-brief writes, acceptance-tests maps to tests, and tdd
ticks off. Every later stage — and loop.py and pipeline.py — reads it, so its shape is a
contract. This module is the one place that shape lives as code; it imports nothing but
the standard library and runs from wherever it is copied.

    python3 brief.py check <brief.md> [--json]

It prints each problem with a stable code and a line number, then the notes — information,
never a failure: every Revisions entry marked `unconfirmed`, a missing Status line, a
missing Ship checklist.

    B01  no `# Build Plan: <name>` title
    B02  `**Status:**` is not `draft — awaiting approval` or `approved[ — <who, how>]`
    B10  a required section is missing
    B11  the Acceptance criteria section has no `- [ ]` criterion
    B20  the Acceptance tests section is filled but names no `- **Command:** `<command>``
    B21  a criterion is not mapped — to a test, or as `Not acceptance-testable` with a reason
    B22  a criterion is mapped more than once
    B23  a line in Acceptance tests is not `- [ ] <criterion> → `<test id>`` or
         `- Not acceptance-testable: <criterion> — <why>`
    B30  a ticked criterion names no test (`- [x] <criterion> — verified by <test name>`)
    B31  a criterion is ticked but `**Base:**` is not a commit
    I01  a Revisions entry is marked `unconfirmed`
    I02  no `**Status:**` line — the brief reads as a draft
    I03  no Ship checklist section

Exit status: 0 clean, 1 problems found, 2 usage error (or no such file).
"""
from __future__ import annotations

import argparse
import dataclasses as dc
import json
import pathlib
import re
import sys

# What loop.py and pipeline.py read from a brief. They import these, so there is one definition.
TITLE_RE = re.compile(r"^# Build Plan:\s*(.+)$", re.M)
STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+)$", re.M)
BASE_RE = re.compile(r"^\*\*Base:\*\*\s*`?([0-9a-f]{7,40})\b", re.M)
ACCEPTANCE_RE = re.compile(r"\*\*Acceptance tests\*\*.*?^- \*\*Command:\*\*\s*`([^`]+)`", re.S | re.M)
SHIP_RE = re.compile(r"\*\*Ship checklist\*\*[^\n]*\n(.*?)(?=\n\s*\n\*\*|\n##|\Z)", re.S)

DASH = "[—–-]+"
STATUS_FORMS = (re.compile(rf"^draft\s*{DASH}\s*awaiting approval\.?$", re.I),
                re.compile(rf"^approved(\s*{DASH}\s*\S.*)?$", re.I))
REQUIRED = ("Summary", "Current behavior", "Desired behavior", "Key interfaces", "Acceptance criteria",
            "Test seams", "Out of scope")
HEADER_RE = re.compile(r"^\*\*([^*]+?):?\*\*:?(.*)$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")
BOX_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s*(.*)$")
ITEM_RE = re.compile(r"^\s*-\s+(.*)$")
COMMAND_RE = re.compile(r"^\*\*Command:\*\*\s*(.*)$")
MAPPED_RE = re.compile(r"^(.*?)\s*(?:→|->)\s*`([^`]+)`")
NOT_TESTABLE_RE = re.compile(r"^Not acceptance-testable:\s*(.*)$", re.I)
VERIFIED_RE = re.compile(rf"\s+{DASH}\s+verified by\s+(\S.*)$", re.I | re.S)
LABEL_RE = re.compile(r"^(tracer bullet|edge case|abuse case|authori[sz]ation|journey)\s*:\s*", re.I)
NUMBERED_RE = re.compile(r"^criterion\s+(\d+)\b", re.I)


@dc.dataclass
class Criterion:
    line: int
    ticked: bool
    text: str          # the whole item, continuation lines folded in


@dc.dataclass
class Brief:
    title: str | None
    status: str | None
    status_line: int
    base: str | None
    sections: dict     # lower-cased name -> (line of its header, [(line, text) of its body])
    criteria: list
    command: str | None


def _items(body):
    """Fold a section's `- ` items and their continuation lines into (line, text) pairs."""
    out = []
    for ln, raw in body:
        if ITEM_RE.match(raw):
            out.append([ln, ITEM_RE.match(raw).group(1).strip()])
        elif out and raw.strip() and raw[:1].isspace():
            out[-1][1] += " " + raw.strip()
    return [(ln, text) for ln, text in out]


def section(brief, name):
    """(header line, body) of the first section whose name starts with `name`; (0, None) when absent."""
    return next((v for k, v in brief.sections.items() if k.startswith(name.lower())), (0, None))


def parse(text):
    sections, current, fenced = {}, None, False
    for ln, raw in enumerate(text.splitlines(), 1):
        if raw.lstrip().startswith("```"):
            fenced = not fenced
        m = None if fenced else (H2_RE.match(raw) or HEADER_RE.match(raw))
        if m:
            current = m.group(1).strip().lower()
            sections.setdefault(current, (ln, []))
        elif current:
            sections[current][1].append((ln, raw))
    status = STATUS_RE.search(text)
    base = BASE_RE.search(text)
    title = TITLE_RE.search(text)
    b = Brief(title.group(1).strip() if title else None, status.group(1).strip() if status else None,
              text.count("\n", 0, status.start()) + 1 if status else 0, base.group(1) if base else None,
              sections, [], None)
    for ln, item in _items(section(b, "acceptance criteria")[1] or []):
        box = BOX_RE.match("- " + item)
        if box:
            b.criteria.append(Criterion(ln, box.group(1) != " ", box.group(2).strip()))
    cmd = ACCEPTANCE_RE.search(text)
    b.command = cmd.group(1).strip() if cmd else None
    return b


def criteria_counts(text):
    """(ticked, total) over the Acceptance criteria section."""
    items = parse(text).criteria
    return sum(1 for c in items if c.ticked), len(items)


def _norm(text):
    text = VERIFIED_RE.sub("", text)
    text = LABEL_RE.sub("", text.strip())
    return re.sub(r"[\s`*_.;:,]+", " ", text.lower()).strip()


def _match(key, criteria):
    """Index of the criterion a mapping line is about, or None when it can't be told."""
    num = NUMBERED_RE.match(LABEL_RE.sub("", key.strip()))
    if num and 1 <= int(num.group(1)) <= len(criteria):
        return int(num.group(1)) - 1
    k = _norm(key)
    if not k:
        return None
    hits = [i for i, c in enumerate(criteria)
            if _norm(c.text) == k or (min(len(k), len(_norm(c.text))) >= 12
                                      and (_norm(c.text).startswith(k) or k.startswith(_norm(c.text))))]
    return hits[0] if len(hits) == 1 else None


def check(text):
    """Returns (problems, notes): lists of (code, line, message)."""
    b, problems, notes = parse(text), [], []
    if not b.title:
        problems.append(("B01", 1, "no `# Build Plan: <name>` title"))
    if b.status is None:
        notes.append(("I02", 0, "no `**Status:**` line — nothing says this brief was approved; it reads as a draft"))
    elif not any(f.match(b.status) for f in STATUS_FORMS):
        problems.append(("B02", b.status_line, f"Status {b.status!r} is neither `draft — awaiting approval` "
                                               "nor `approved[ — <who, how>]`"))
    for name in REQUIRED:
        if section(b, name)[1] is None:
            problems.append(("B10", 0, f"no **{name}** section"))
    rev_line, revisions = section(b, "revisions")
    if revisions is None:
        problems.append(("B10", 0, "no `## Revisions` section"))
    if section(b, "ship checklist")[1] is None:
        notes.append(("I03", 0, "no **Ship checklist** section — rollout, rollback, observability and docs "
                                "are not recorded as decided"))
    crit_line, crit_body = section(b, "acceptance criteria")
    if crit_body is not None and not b.criteria:
        problems.append(("B11", crit_line, "the Acceptance criteria section has no `- [ ]` criterion"))

    # --- the Acceptance tests mapping, once stage 3 has filled it
    acc_line, acc_body = section(b, "acceptance tests")
    lines, command_seen = [], False
    for ln, item in _items(acc_body or []):
        if COMMAND_RE.match(item):
            command_seen = True
        else:
            lines.append((ln, item))
    if acc_body is not None and (b.command or lines):
        if not b.command:
            problems.append(("B20", acc_line, "the Acceptance tests section is filled but names no "
                                              "`- **Command:** `<command>``" + (
                                                  " (the Command line is still empty)" if command_seen else "")))
        mapped, loose = {}, 0
        for ln, item in lines:
            box = BOX_RE.match("- " + item)
            body = box.group(2) if box else item
            nt = None if box else NOT_TESTABLE_RE.match(body)
            mm = MAPPED_RE.match(body) if box else None
            if nt:
                rest = nt.group(1)
                if not re.search(rf"\S\s+{DASH}\s+\S", rest):
                    problems.append(("B23", ln, "`Not acceptance-testable:` names no reason "
                                                "(`<criterion> — <why>`)"))
                idx = next((i for i, c in enumerate(b.criteria)
                            if len(_norm(c.text)) >= 12 and _norm(rest).startswith(_norm(c.text))), None)
                if idx is None:
                    idx = _match(re.split(rf"\s+{DASH}\s+", rest)[0], b.criteria)
            elif mm:
                if LABEL_RE.match(mm.group(1).strip()) and mm.group(1).strip().lower().startswith("journey"):
                    continue                        # a Journey line is extra: it maps no criterion
                idx = _match(mm.group(1), b.criteria)
            else:
                problems.append(("B23", ln, f"not a mapping line: {item[:60]!r} — expected "
                                            "`- [ ] <criterion> → `<test id>`` or "
                                            "`- Not acceptance-testable: <criterion> — <why>`"))
                continue
            if idx is None:
                loose += 1
            else:
                mapped.setdefault(idx, []).append(ln)
        if loose:
            # Some lines name their criterion in words we can't tie to one: fall back to counting.
            total = loose + sum(len(v) for v in mapped.values())
            if total < len(b.criteria):
                problems.append(("B21", acc_line, f"{len(b.criteria)} criteria but {total} mapping line(s) — "
                                                  "every criterion is mapped to a test or listed as not "
                                                  "acceptance-testable"))
            elif total > len(b.criteria):
                problems.append(("B22", acc_line, f"{len(b.criteria)} criteria but {total} mapping line(s) — "
                                                  "every criterion appears exactly once"))
        else:
            for i, c in enumerate(b.criteria):
                if i not in mapped:
                    problems.append(("B21", c.line, f"criterion {i + 1} is not mapped: {c.text[:60]!r}"))
        for i, lns in mapped.items():
            for ln in lns[1:]:
                problems.append(("B22", ln, f"criterion {i + 1} is already mapped on line {lns[0]}"))

    # --- tdd's ticks
    ticked = [c for c in b.criteria if c.ticked]
    for c in ticked:
        if not VERIFIED_RE.search(c.text):
            problems.append(("B30", c.line, "ticked without naming its test — "
                                            "`- [x] <criterion> — verified by <test name>`"))
    if ticked and not b.base:
        m = re.search(r"^\*\*Base:\*\*.*$", text, re.M)
        problems.append(("B31", text.count("\n", 0, m.start()) + 1 if m else 0,
                         f"{len(ticked)} criterion/criteria ticked but `**Base:**` names no commit — tdd records "
                         "the commit the change is measured against before its first slice"))

    for ln, item in _items(revisions or []):
        if re.search(r"\bunconfirmed\b", item, re.I):
            notes.append(("I01", ln, f"unconfirmed: {item[:160]}"))
    key = lambda p: (p[1], p[0])
    return sorted(problems, key=key), sorted(notes, key=key)


def _fmt(p):
    code, line, msg = p
    return f"{code} {f'line {line}' if line else 'brief'}: {msg}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="verify the brief's shape")
    c.add_argument("brief")
    c.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    path = pathlib.Path(a.brief)
    if not path.is_file():
        print(f"brief.py: no such file: {path}", file=sys.stderr)
        return 2
    problems, notes = check(path.read_text())
    if a.json:
        print(json.dumps({"problems": [_fmt(p) for p in problems], "notes": [_fmt(n) for n in notes]}, indent=2))
    else:
        for p in problems:
            print("error:", _fmt(p))
        for n in notes:
            print("note:", _fmt(n))
        print(f"{len(problems)} problem(s), {len(notes)} note(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
