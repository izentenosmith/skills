#!/usr/bin/env python3
"""Read, check, judge and write a .workflow/ledger.md.

The ledger is an append-only event log; the grammar is in LEDGER.md next to this
file. This module is the single place that grammar lives: loop.py writes through
the render_* functions and reads back through parse()/replay(), and anyone running
the skills by hand can check their ledger with the CLI.

    python3 ledger.py check  <ledger.md> [--against <older.md>] [--cap 3] [--json]
    python3 ledger.py status <ledger.md> [--cap 3] [--json]
    python3 ledger.py next-id <ledger.md> F|N

Exit status: 0 clean, 1 errors found, 2 usage error.
"""
from __future__ import annotations

import argparse
import dataclasses as dc
import json
import pathlib
import re
import sys

CAP = 3
SEVERITIES = ("blocker", "major", "minor")
VERDICTS = ("CONFIRMED", "REFUTED", "INCONCLUSIVE")
OUTCOMES = ("GO", "NO-GO", "ESCALATED")
SMELL_ACTIONS = ("left", "promoted", "retired")

# A section's key is what loop.py and the stage derivation use; the heading text is
# matched by prefix, so "Findings (unadjudicated)" and "Findings" are the same section.
SECTIONS = {
    "closed slices": "closed",
    "smells": "smells",
    "findings": "findings",
    "surfaces": "surfaces",
    "verdicts": "verdicts",
    "remediation slices": "slices",
    "decisions": "decisions",
}
STAGE_SECTIONS = ("closed", "smells", "findings", "verdicts")  # stage → its proof of completion

ITER_RE = re.compile(r"^## Iteration (\d+)\s*$")
H2_RE = re.compile(r"^## ")
SECTION_RE = re.compile(r"^### (.+?)\s*$")
OUTCOME_RE = re.compile(r"^verdict:\s*(GO|NO-GO|ESCALATED)\s*$", re.I)
ENTRY_RE = re.compile(r"^#### (F\d+)(?:\s*\((re-examined)\))?(?:\s+—\s+(.*?))?\s*$")
FIELD_RE = re.compile(r"^- \*\*(.+?):\*\*\s*(.*)$")
NONE_RE = re.compile(r"^- none\s*$", re.I)
SMELL_RE = re.compile(r"^- \*\*(N\d+)\*\*\s+(.*)$")
SMELL_ACTION_RE = re.compile(r"^—\s*(left|promoted|retired)\b[^:]*:\s*(.*)$", re.I)
SMELL_NOTED_RE = re.compile(r"^(.*?)\s+—\s+noted\b[^:]*:\s*(.*)$", re.I)
SLICE_RE = re.compile(r"^- (?:\[ \]\s*)?\[(blocker|major|minor)\]\s+(F\d+)\s+—\s+(.+)$", re.I)
CLOSED_RE = re.compile(r"^- \[x\]\s+(F\d+)\s+—\s+(.*)$", re.I)
SURFACE_RE = re.compile(r"^- \*\*(Swept|Unattacked):\*\*\s*(.+)$", re.I)
DECISION_RE = re.compile(r"^- \*\*(F\d+)\*\*\s+—\s+waived:\s*(.+)$", re.I)
ID_RE = re.compile(r"\b([FN])(\d+)\b")


# ------------------------------------------------------------------ data model

@dc.dataclass
class Entry:
    """A `#### F<id>` block — a finding, or a verdict on one."""
    fid: str
    head: str            # text after the em dash in the heading ('' if none)
    reexamined: bool
    fields: dict
    line: int


@dc.dataclass
class Iteration:
    n: int
    line: int
    sections: dict = dc.field(default_factory=dict)   # key -> list of parsed items
    order: list = dc.field(default_factory=list)      # section keys in file order
    outcome: str | None = None
    outcome_reason: str = ""


@dc.dataclass
class Ledger:
    preamble: str
    iterations: list
    reserved: set
    problems: list       # parse-time errors: (code, iteration, line, message)

    def ids(self, kind):
        seen = {int(m[1]) for m in ID_RE.findall(self.preamble) if m[0] == kind} | {
            int(i[1:]) for i in self.reserved if i[0] == kind}
        for it in self.iterations:
            if kind == "F":
                seen |= {int(f.fid[1:]) for f in it.sections.get("findings", [])}
            else:
                seen |= {int(s["id"][1:]) for s in it.sections.get("smells", [])}
        return seen

    def next_id(self, kind):
        return f"{kind}{max(self.ids(kind), default=0) + 1}"


# ------------------------------------------------------------------ parsing

def parse(text: str) -> Ledger:
    lines = text.splitlines()
    problems = []
    first = next((i for i, l in enumerate(lines) if ITER_RE.match(l)), len(lines))
    preamble = "\n".join(lines[:first])
    reserved = {f"{k}{n}" for k, n in ID_RE.findall(preamble)}

    iterations, it, key, entry, last_field = [], None, None, None, None
    for idx in range(first, len(lines)):
        raw, ln = lines[idx], idx + 1
        line = raw.rstrip()
        if not line.strip():
            continue
        m = ITER_RE.match(line)
        if m:
            it = Iteration(int(m.group(1)), ln)
            iterations.append(it)
            key = entry = None
            continue
        if H2_RE.match(line):
            problems.append(("E03", it.n if it else 0, ln, f"unexpected heading inside the log: {line!r}"))
            key = entry = None
            continue
        m = SECTION_RE.match(line)
        if m:
            entry = None
            title = m.group(1).strip()
            om = OUTCOME_RE.match(title)
            if om:
                it.outcome, key = om.group(1).upper(), "outcome"
                it.order.append("outcome")
                continue
            key = next((v for k, v in SECTIONS.items() if title.lower().startswith(k)), None)
            if key is None:
                problems.append(("E03", it.n, ln, f"unknown section {title!r}"))
                continue
            if key in it.sections:
                problems.append(("E03", it.n, ln, f"section {title!r} appears twice in iteration {it.n}"))
            it.sections.setdefault(key, [])
            it.order.append(key)
            continue
        if key is None:
            problems.append(("E04", it.n, ln, f"text outside any section: {line.strip()[:60]!r}"))
            continue
        if NONE_RE.match(line.strip()):
            continue

        if key == "outcome":
            fm = FIELD_RE.match(line.strip())
            if fm and fm.group(1).lower() == "reason":
                it.outcome_reason = fm.group(2)
            elif it.outcome_reason and raw[:1].isspace():
                it.outcome_reason += " " + line.strip()
            continue

        if key in ("findings", "verdicts"):
            em = ENTRY_RE.match(line)
            if em:
                entry, last_field = Entry(em.group(1), (em.group(3) or "").strip(), bool(em.group(2)), {}, ln), None
                it.sections[key].append(entry)
                continue
            fm = FIELD_RE.match(line.strip())
            if entry and fm and not raw[:1].isspace():
                last_field = fm.group(1).strip().lower()
                entry.fields[last_field] = fm.group(2).strip()
                continue
            if entry and raw[:1].isspace() and last_field in entry.fields:
                entry.fields[last_field] += " " + line.strip()
                continue
            problems.append(("E04", it.n, ln, f"malformed line in {key}: {line.strip()[:60]!r}"))
            continue

        if key == "smells":
            sm = SMELL_RE.match(line.strip()) if not raw.startswith("  ") else None
            if sm:
                sid, rest = sm.group(1), sm.group(2).strip()
                am = SMELL_ACTION_RE.match(rest)
                nm = SMELL_NOTED_RE.match(rest)
                if am:
                    it.sections["smells"].append({"id": sid, "kind": am.group(1).lower(), "text": am.group(2), "line": ln})
                elif nm:
                    it.sections["smells"].append({"id": sid, "kind": "noted", "what": nm.group(1),
                                                  "text": nm.group(2), "promote_if": "", "line": ln})
                else:
                    problems.append(("E04", it.n, ln, f"smell {sid} is neither noted nor left/promoted/retired"))
                continue
            fm = FIELD_RE.match(line.strip())
            last = it.sections["smells"][-1] if it.sections["smells"] else None
            if fm and last and last["kind"] == "noted" and fm.group(1).lower() == "promote if":
                last["promote_if"] = fm.group(2).strip()
                continue
            if last and raw[:1].isspace():
                last["promote_if" if last.get("promote_if") else "text"] += " " + line.strip()
                continue
            problems.append(("E04", it.n, ln, f"malformed line in smells: {line.strip()[:60]!r}"))
            continue

        simple = {"slices": SLICE_RE, "closed": CLOSED_RE, "surfaces": SURFACE_RE, "decisions": DECISION_RE}[key]
        pm = simple.match(line.strip())
        items = it.sections[key]
        if pm and not raw.startswith("  "):
            g = pm.groups()
            items.append({"slices": lambda: {"severity": g[0].lower(), "id": g[1], "text": g[2], "line": ln},
                          "closed": lambda: {"id": g[0], "text": g[1], "line": ln},
                          "surfaces": lambda: {"kind": g[0].lower(), "text": g[1], "line": ln},
                          "decisions": lambda: {"id": g[0], "text": g[1], "line": ln}}[key]())
        elif items and raw[:1].isspace():
            items[-1]["text"] += " " + line.strip()
        else:
            problems.append(("E04", it.n, ln, f"malformed line in {key}: {line.strip()[:60]!r}"))

    return Ledger(preamble, iterations, reserved, problems)


# ------------------------------------------------------------------ replay

@dc.dataclass
class FindingState:
    fid: str
    defined: int
    fields: dict
    verdicts: list = dc.field(default_factory=list)   # (iteration, verdict, severity)
    slice: dict | None = None
    slice_iter: int = 0
    closed: int = 0                                     # iteration it closed in
    waived: bool = False

    @property
    def latest(self):
        return self.verdicts[-1] if self.verdicts else None

    def open_confirmed(self):
        v = self.latest
        return bool(v and v[1] == "CONFIRMED" and not self.closed and not self.waived)

    def open_inconclusive(self):
        v = self.latest
        return bool(v and v[1] == "INCONCLUSIVE" and not self.waived)

    def inconclusive_count(self):
        return sum(1 for v in self.verdicts if v[1] == "INCONCLUSIVE")


@dc.dataclass
class State:
    findings: dict = dc.field(default_factory=dict)
    smells: dict = dc.field(default_factory=dict)       # id -> {"status", "what", "promote_if", "since"}
    computed: dict = dc.field(default_factory=dict)     # iteration -> (outcome, reason)
    progress: dict = dc.field(default_factory=dict)     # iteration -> count closed this pass

    def open_blocking(self):
        return [f for f in self.findings.values()
                if f.open_confirmed() and f.latest[2] in ("blocker", "major")]

    def open_minor(self):
        return [f for f in self.findings.values() if f.open_confirmed() and f.latest[2] == "minor"]

    def open_inconclusive(self):
        return [f for f in self.findings.values() if f.open_inconclusive()]

    def open_slices(self):
        return [f for f in self.findings.values() if f.slice and not f.closed and not f.waived]

    def refuted(self):
        return [f for f in self.findings.values() if f.latest and f.latest[1] == "REFUTED"]

    def active_smells(self):
        return {k: v for k, v in self.smells.items() if v["status"] in ("noted", "left")}


def judge(state: State, n: int, cap: int = CAP):
    """The verdict at the end of iteration n. Pure arithmetic over the replayed state."""
    blocking, inconc = state.open_blocking(), state.open_inconclusive()
    twice = [f.fid for f in inconc if f.inconclusive_count() >= 2]
    if twice:
        return "ESCALATED", f"{', '.join(twice)} came back INCONCLUSIVE a second time — this is the user's call"
    if n >= cap and (blocking or inconc):
        still = [f.fid for f in blocking + inconc]
        return "ESCALATED", (f"iteration {n} of {cap} still has {len(still)} finding(s) open "
                             f"({', '.join(still)}) — the plan, not the code, is the likely problem")
    if n >= 2 and state.progress.get(n, 0) == 0 and (blocking or inconc):
        return "ESCALATED", f"iteration {n} closed nothing while findings stay open — the loop has stalled"
    if blocking or inconc:
        parts = []
        if blocking:
            parts.append(f"{len(blocking)} confirmed blocker/major open ({', '.join(f.fid for f in blocking)})")
        if inconc:
            parts.append(f"{len(inconc)} INCONCLUSIVE open ({', '.join(f.fid for f in inconc)})")
        return "NO-GO", "; ".join(parts)
    minors = state.open_minor()
    return "GO", ("nothing open" if not minors else
                  f"no blocker or major open; {len(minors)} minor(s) ship as tracked: "
                  + ", ".join(f.fid for f in minors))


def replay(ledger: Ledger, cap: int = CAP):
    """Walk the log top to bottom. Returns (state, errors, warnings)."""
    errors = list(ledger.problems)
    warnings = []
    st = State()
    if ledger.preamble.strip() and ledger.iterations:
        if any(l.strip() and not l.startswith("#") for l in ledger.preamble.splitlines()):
            warnings.append(("W01", 0, 0, "preamble carries prose; it is context for agents, not parsed state"))

    for i, it in enumerate(ledger.iterations):
        n = it.n
        if n != i + 1:
            errors.append(("E01", n, it.line, f"iteration {n} where {i + 1} was expected"))
        if n > cap:
            errors.append(("E02", n, it.line, f"iteration {n} exceeds the cap of {cap}"))
        progress = 0

        for c in it.sections.get("closed", []):
            f = st.findings.get(c["id"])
            if not f or not f.slice:
                errors.append(("E32", n, c["line"], f"{c['id']} closed but no remediation slice was opened for it"))
                continue
            if f.closed:
                errors.append(("E32", n, c["line"], f"{c['id']} already closed in iteration {f.closed}"))
                continue
            if not re.search(r"verified by", c["text"], re.I):
                errors.append(("E32", n, c["line"], f"{c['id']} closed without naming the test that verifies it"))
            f.closed = n
            progress += 1

        if "smells" in it.sections:
            touched = set()
            for s in it.sections["smells"]:
                sid = s["id"]
                if s["kind"] == "noted":
                    if sid in st.smells or sid in ledger.reserved:
                        errors.append(("E40", n, s["line"], f"smell id {sid} is already in use"))
                        continue
                    if not s["promote_if"]:
                        errors.append(("E40", n, s["line"], f"noted smell {sid} has no **Promote if:** condition"))
                    st.smells[sid] = {"status": "noted", "what": s["what"], "promote_if": s["promote_if"],
                                      "since": n, "reason": s["text"]}
                else:
                    sm = st.smells.get(sid)
                    if not sm:
                        errors.append(("E41", n, s["line"], f"{s['kind']} names unknown smell {sid}"))
                    elif sm["status"] in ("promoted", "retired"):
                        errors.append(("E41", n, s["line"], f"{sid} was already {sm['status']}"))
                    else:
                        sm["status"] = s["kind"]
                    touched.add(sid)
            for sid, sm in st.smells.items():
                if sm["since"] < n and sid not in touched and sm["status"] in ("noted", "left"):
                    errors.append(("E42", n, it.line, f"carried smell {sid} was not re-examined in iteration {n}"))

        for e in it.sections.get("findings", []):
            known = st.findings.get(e.fid)
            if e.reexamined:
                if not known or not known.open_inconclusive():
                    errors.append(("E10", n, e.line, f"{e.fid} (re-examined) but it is not an open INCONCLUSIVE"))
                else:
                    known.fields.update({k: v for k, v in e.fields.items()})
                continue
            if known or e.fid in ledger.reserved:
                errors.append(("E10", n, e.line, f"finding id {e.fid} is already in use"))
                continue
            f = FindingState(e.fid, n, dict(e.fields))
            st.findings[e.fid] = f
            for req in ("target", "claim challenged", "evidence", "confidence", "severity hint"):
                if not e.fields.get(req):
                    errors.append(("E11", n, e.line, f"{e.fid} is missing **{req.capitalize()}:**"))
            conf = e.fields.get("confidence", "").lower()
            if conf and conf not in ("proven", "unproven"):
                errors.append(("E12", n, e.line, f"{e.fid} confidence {conf!r} is not proven/unproven"))
            hint = e.fields.get("severity hint", "").lower()
            if hint and hint not in SEVERITIES:
                errors.append(("E12", n, e.line, f"{e.fid} severity hint {hint!r} is not blocker/major/minor"))
            if conf == "unproven" and not e.fields.get("would be settled by"):
                errors.append(("E13", n, e.line, f"{e.fid} is unproven and names nothing that would settle it"))
            reopens = e.fields.get("reopens", "")
            if reopens:
                rid = re.match(r"F\d+", reopens.strip())
                target = st.findings.get(rid.group(0)) if rid else None
                if not target or not target.latest or target.latest[1] != "REFUTED":
                    errors.append(("E14", n, e.line, f"{e.fid} reopens {reopens!r}, which is not a refuted finding"))

        if "verdicts" in it.sections:
            seen = {}
            for v in it.sections["verdicts"]:
                f = st.findings.get(v.fid)
                if not f:
                    errors.append(("E20", n, v.line, f"verdict on {v.fid}, which no finding defines"))
                    continue
                if v.fid in seen:
                    errors.append(("E26", n, v.line, f"{v.fid} has a second verdict in iteration {n}"))
                    continue
                seen[v.fid] = v
                parts = v.head.split()
                kind = parts[0].upper() if parts else ""
                sev = parts[1].lower() if len(parts) > 1 else ""
                if kind not in VERDICTS:
                    errors.append(("E20", n, v.line, f"{v.fid} verdict {v.head!r} is not CONFIRMED/REFUTED/INCONCLUSIVE"))
                    continue
                if f.latest and f.latest[1] == "REFUTED":
                    errors.append(("E21", n, v.line, f"{v.fid} was REFUTED in iteration {f.latest[0]}; "
                                                     "a refuted finding is not re-adjudicated"))
                    continue
                if f.latest and f.latest[1] == "CONFIRMED":
                    errors.append(("E21", n, v.line, f"{v.fid} was already CONFIRMED in iteration {f.latest[0]}"))
                    continue
                if not v.fields.get("reason"):
                    errors.append(("E22", n, v.line, f"{v.fid} verdict has no **Reason:**"))
                if kind == "REFUTED" and not v.fields.get("reopens only if"):
                    errors.append(("E22", n, v.line, f"{v.fid} REFUTED without **Reopens only if:**"))
                if kind == "INCONCLUSIVE" and not v.fields.get("settled by"):
                    errors.append(("E23", n, v.line, f"{v.fid} INCONCLUSIVE without **Settled by:**"))
                if kind == "CONFIRMED" and sev not in SEVERITIES:
                    errors.append(("E24", n, v.line, f"{v.fid} CONFIRMED without a blocker/major/minor severity"))
                prev = f.latest
                if prev and prev[1] == "INCONCLUSIVE" and kind != "INCONCLUSIVE":
                    progress += 1                       # an INCONCLUSIVE settled either way
                if kind == "CONFIRMED":
                    progress += 1                       # newly confirmed
                f.verdicts.append((n, kind, sev if kind == "CONFIRMED" else ""))
                if f.inconclusive_count() > 2:
                    errors.append(("E27", n, v.line, f"{v.fid} INCONCLUSIVE a third time; it should have escalated"))
            for e in it.sections.get("findings", []):
                if e.fid not in seen and e.fid in st.findings and not (
                        st.findings[e.fid].latest and st.findings[e.fid].latest[1] == "REFUTED"
                        and st.findings[e.fid].latest[0] < n):
                    errors.append(("E25", n, e.line, f"{e.fid} was reported in iteration {n} but never adjudicated"))
            for f in st.findings.values():
                if f.open_inconclusive() and f.latest[0] < n and f.fid not in seen:
                    errors.append(("E25", n, it.line, f"{f.fid} is an open INCONCLUSIVE with no verdict in iteration {n}"))

        sliced = set()
        for s in it.sections.get("slices", []):
            f = st.findings.get(s["id"])
            if not f or not f.latest or f.latest[0] != n or f.latest[1] != "CONFIRMED":
                errors.append(("E31", n, s["line"], f"slice for {s['id']}, which was not CONFIRMED in iteration {n}"))
                continue
            if s["severity"] != f.latest[2]:
                errors.append(("E31", n, s["line"], f"slice for {s['id']} says {s['severity']}, verdict says {f.latest[2]}"))
            f.slice, f.slice_iter = s, n
            sliced.add(s["id"])
        if "verdicts" in it.sections:
            for f in st.findings.values():
                if f.latest and f.latest[0] == n and f.latest[1] == "CONFIRMED" and f.fid not in sliced:
                    errors.append(("E30", n, it.line, f"{f.fid} is CONFIRMED with no remediation slice"))

        for d in it.sections.get("decisions", []):
            f = st.findings.get(d["id"])
            if not f:
                errors.append(("E20", n, d["line"], f"waiver for unknown finding {d['id']}"))
            else:
                f.waived = True

        st.progress[n] = progress
        if "verdicts" in it.sections or it.outcome:
            st.computed[n] = judge(st, n, cap)
        if it.outcome:
            if "verdicts" not in it.sections:
                errors.append(("E51", n, it.line, f"iteration {n} states a verdict but has no ### Verdicts section"))
            elif it.outcome != st.computed[n][0]:
                errors.append(("E50", n, it.line, f"stated {it.outcome}, computed {st.computed[n][0]}: {st.computed[n][1]}"))
        elif i < len(ledger.iterations) - 1:
            errors.append(("E51", n, it.line, f"iteration {n} ends without a verdict but a later iteration follows"))

    return st, errors, warnings


# ------------------------------------------------------------------ status

def next_stage(ledger: Ledger, state: State):
    """Where the loop resumes. Returns (iteration, stage) — stage is one of
    fix, refactor, teardown, verdict, done, escalated."""
    if not ledger.iterations:
        return 1, "refactor"
    it = ledger.iterations[-1]
    if it.outcome == "GO":
        return it.n, "done"
    if it.outcome == "ESCALATED":
        return it.n, "escalated"
    if it.outcome == "NO-GO":
        return it.n + 1, ("fix" if state.open_slices() else "teardown")
    present = set(it.sections)
    if "verdicts" in present:
        return it.n, "verdict"            # verdicts written, outcome line missing
    if "findings" in present:
        return it.n, "verdict"
    if "smells" in present:
        return it.n, "teardown"
    if "closed" in present:
        return it.n, "refactor"
    return it.n, ("fix" if state.open_slices() else "refactor")


def status(text: str, cap: int = CAP):
    led = parse(text)
    st, errors, warnings = replay(led, cap)
    n, stage = next_stage(led, st)
    last = led.iterations[-1].n if led.iterations else 0
    return {
        "iteration": n,
        "next_stage": stage,
        "computed": dict(zip(("outcome", "reason"), st.computed[last])) if last in st.computed else None,
        "open_blocking": [f.fid for f in st.open_blocking()],
        "open_minor": [f.fid for f in st.open_minor()],
        "open_inconclusive": [f.fid for f in st.open_inconclusive()],
        "open_slices": [{"id": f.fid, "severity": f.slice["severity"], "behavior": f.slice["text"]}
                        for f in st.open_slices()],
        "refuted": [{"id": f.fid, "claim": f.fields.get("claim challenged", ""),
                     "reopens_only_if": _verdict_field(led, f.fid, "reopens only if")} for f in st.refuted()],
        "inconclusive": [{"id": f.fid, "claim": f.fields.get("claim challenged", ""),
                          "settled_by": _verdict_field(led, f.fid, "settled by"),
                          "pass": f.inconclusive_count()} for f in st.open_inconclusive()],
        "carried_smells": [{"id": k, **{x: v[x] for x in ("status", "what", "promote_if", "since")}}
                           for k, v in st.active_smells().items()],
        "next_ids": {"F": led.next_id("F"), "N": led.next_id("N")},
        "errors": [_fmt(e) for e in errors],
        "warnings": [_fmt(w) for w in warnings],
    }


def _verdict_field(led, fid, field):
    for it in reversed(led.iterations):
        for v in reversed(it.sections.get("verdicts", [])):
            if v.fid == fid and field in v.fields:
                return v.fields[field]
    return ""


def _fmt(e):
    code, n, line, msg = e
    where = f"line {line}" if line else "ledger"
    return f"{code} {where}{f' (iteration {n})' if n else ''}: {msg}"


def append_only(old: str, new: str):
    base = old.rstrip()
    return new.startswith(base), base


# ------------------------------------------------------------------ rendering
# Every write the harness makes goes through these, so it can only write the grammar.

def _value(v):
    """Fold a multi-line value into continuation lines."""
    lines = [l.strip() for l in str(v).strip().splitlines() if l.strip()]
    return "\n  ".join(lines) if lines else "—"


def _field(k, v):
    return f"- **{k}:** {_value(v)}"


def render_header(title):
    return f"# Ledger — {title}\n"


def render_iteration(n):
    return f"\n## Iteration {n}\n"


def render_closed(items):
    body = [f"- [x] {c['finding']} — verified by `{c['test']}`" for c in items] or ["- none"]
    return "\n### Closed slices\n" + "\n".join(body) + "\n"


def render_smells(noted, actions):
    """noted: [{id, smell, location, reason, promote_if}]; actions: [{id, action, reason}]"""
    body = [f"- **{a['id']}** — {a['action']}: {_value(a['reason'])}" for a in actions]
    for s in noted:
        body.append(f"- **{s['id']}** {s['smell']} at {s['location']} — noted: {_value(s['reason'])}")
        body.append(f"  - **Promote if:** {_value(s['promote_if'])}")
    return "\n### Smells\n" + ("\n".join(body) or "- none") + "\n"


def render_findings(findings):
    out = ["\n### Findings (unadjudicated)"]
    if not findings:
        out.append("- none")
    for f in findings:
        out.append(f"#### {f['id']}{' (re-examined)' if f.get('reexamines') else ''}")
        out.append(_field("Target", f["target"]))
        out.append(_field("Claim challenged", f["claim"]))
        out.append(_field("Evidence", f["evidence"]))
        if f.get("breaking_case"):
            out.append(_field("Breaking case", f["breaking_case"]))
        out.append(_field("Confidence", f["confidence"]))
        if f.get("settled_by") or f["confidence"] == "unproven":
            out.append(_field("Would be settled by", f.get("settled_by") or "—"))
        out.append(_field("Severity hint", f["severity_hint"]))
        if f.get("reopens"):
            out.append(_field("Reopens", f["reopens"]))
        if f.get("surface"):
            out.append(_field("Surface", f["surface"]))
    return "\n".join(out) + "\n"


def render_surfaces(swept, unattacked):
    body = [f"- **Swept:** {s['surface']} — {_value(s.get('note') or 'found nothing')}" for s in swept]
    body += [f"- **Unattacked:** {s['surface']} — {_value(s['reason'])}" for s in unattacked]
    return "\n### Surfaces\n" + ("\n".join(body) or "- none") + "\n"


def render_verdicts(verdicts):
    out = ["\n### Verdicts"]
    if not verdicts:
        out.append("- none")
    for v in verdicts:
        head = v["verdict"] + (f" {v['severity']}" if v["verdict"] == "CONFIRMED" else "")
        out.append(f"#### {v['finding']} — {head}")
        out.append(_field("Reason", v["reason"]))
        if v["verdict"] == "REFUTED":
            out.append(_field("Reopens only if", v.get("reopens_only_if") or "—"))
        if v["verdict"] == "INCONCLUSIVE":
            out.append(_field("Settled by", v.get("settled_by") or "—"))
            if v.get("pass"):
                out.append(_field("Pass", v["pass"]))
        if v.get("verification"):
            out.append(_field("Verification", v["verification"]))
    return "\n".join(out) + "\n"


def render_slices(slices):
    body = [f"- [ ] [{s['severity']}] {s['finding']} — {_value(s['behavior'])}" for s in slices]
    return "\n### Remediation slices\n" + ("\n".join(body) or "- none") + "\n"


def render_outcome(outcome, reason, note=""):
    out = f"\n### Verdict: {outcome}\n{_field('Reason', reason)}\n"
    if note:
        out += _field("Note", note) + "\n"
    return out


# ------------------------------------------------------------------ CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="validate the grammar and the loop rules")
    c.add_argument("ledger")
    c.add_argument("--against", help="an older copy; the ledger must extend it (append-only)")
    c.add_argument("--cap", type=int, default=CAP)
    c.add_argument("--json", action="store_true")
    s = sub.add_parser("status", help="replayed state and where the loop resumes")
    s.add_argument("ledger")
    s.add_argument("--cap", type=int, default=CAP)
    s.add_argument("--json", action="store_true")
    i = sub.add_parser("next-id", help="the next free finding or smell id")
    i.add_argument("ledger")
    i.add_argument("kind", choices=["F", "N"])
    a = ap.parse_args(argv)

    path = pathlib.Path(a.ledger)
    text = path.read_text() if path.exists() else ""

    if a.cmd == "next-id":
        print(parse(text).next_id(a.kind))
        return 0

    rep = status(text, a.cap)
    if a.cmd == "check" and a.against:
        ok, _ = append_only(pathlib.Path(a.against).read_text(), text)
        if not ok:
            rep["errors"].append("E60 ledger: the older copy is not a prefix — something above the end was rewritten")

    if a.json:
        print(json.dumps(rep, indent=2))
    elif a.cmd == "check":
        for w in rep["warnings"]:
            print("warning:", w)
        for e in rep["errors"]:
            print("error:", e)
        print(f"{len(rep['errors'])} error(s), {len(rep['warnings'])} warning(s)")
    else:
        comp = rep["computed"]
        print(f"iteration {rep['iteration']} · next stage: {rep['next_stage']}")
        if comp:
            print(f"computed verdict: {comp['outcome']} — {comp['reason']}")
        for k in ("open_blocking", "open_inconclusive", "open_minor"):
            if rep[k]:
                print(f"{k.replace('_', ' ')}: {', '.join(rep[k])}")
        for sl in rep["open_slices"]:
            print(f"open slice: [{sl['severity']}] {sl['id']} — {sl['behavior']}")
        for sm in rep["carried_smells"]:
            print(f"carried smell: {sm['id']} {sm['what']} (promote if: {sm['promote_if']})")
        if rep["errors"]:
            print(f"{len(rep['errors'])} error(s) — run `check` for detail")
    return 1 if rep["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
