#!/usr/bin/env python3
"""Keep an incident log whose times come from the clock and whose rules are checked.

The incident-fix skill asks for a durable, UTC-stamped, append-only log in which every
production action follows its own confirmation. Asked in prose, a model under pressure
writes times from memory and logs an action it was never cleared to take. This tool
makes both mechanical: `log` stamps entries from the system clock and refuses a
production action that has no confirmation of its own, `check` validates the whole log,
and `timeline` hands the post-mortem its spine. The format is the one in
skills/operations/incident-fix/incident-log.md.

    python3 incident.py new      <log.md> --title T --severity SEV2 --why W --detected-by "alert — source" [--tracker ID]
    python3 incident.py log      <log.md> <kind> <text…> [--at ISO]   (--at only for impact-start / change)
    python3 incident.py factor   <log.md> "<factor>" --follow-up "<outcome>" --owner O --due D [--where W]
    python3 incident.py factor   <log.md> "<factor>" --accepted "<reason>" --by WHO [--revisit WHEN]
    python3 incident.py check    <log.md> [--json]
    python3 incident.py timeline <log.md>

Exit status: 0 ok · 1 refused or errors found · 2 usage error.
"""
from __future__ import annotations

import argparse
import dataclasses as dc
import datetime as dt
import json
import pathlib
import re
import sys

KINDS = ("detected", "impact-start", "change", "phase", "evidence", "finding", "proposed", "confirmed",
         "action[prod]", "action", "result", "comms", "severity", "mitigated", "resolved", "closed", "note")
BACKFILL = ("impact-start", "change")
PHASES = ("contain", "diagnose", "fix", "learn")
MILESTONES = ("mitigated", "resolved", "closed")

TS = r"\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d)?Z"
ENTRY_RE = re.compile(rf"^- ({TS}) · (\S+) · (.*)$")
FIELD_RE = re.compile(r"^- \*\*(.+?):\*\*\s*(.*)$")
FACTOR_RE = re.compile(r"^- \*\*(C\d+)\*\* (.+?) → (follow-up|accepted risk): (.+)$")
USER_DETECTED = re.compile(r"\b(user|customer|client|support|engineer|human|report)", re.I)
DETECTION_FIX = re.compile(r"\b(alert|monitor|detect|alarm|probe|health ?check|observab)", re.I)


class Refused(Exception):
    pass


@dc.dataclass
class Entry:
    at: dt.datetime
    kind: str
    text: str
    line: int


@dc.dataclass
class Log:
    fields: dict
    entries: list
    factors: list
    problems: list


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def parse(text):
    fields, entries, factors, problems = {}, [], [], []
    section = "header"
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if line.startswith("## "):
            title = line[3:].strip().lower()
            section = "log" if title == "log" else "factors" if title.startswith("contributing") else "other"
            continue
        if not line.strip() or line.startswith("# "):
            continue
        if section == "header":
            m = FIELD_RE.match(line)
            if m:
                fields[m.group(1).lower()] = m.group(2)
        elif section == "log":
            m = ENTRY_RE.match(line)
            if m:
                entries.append(Entry(parse_time(m.group(1)), m.group(2), m.group(3), i))
            elif raw[:1].isspace() and entries:
                entries[-1].text += " " + line.strip()
            else:
                problems.append(("I02", i, f"not a log entry: {line.strip()[:70]!r}"))
        elif section == "factors":
            m = FACTOR_RE.match(line)
            if m:
                factors.append({"id": m.group(1), "factor": m.group(2), "outcome": m.group(3),
                                "detail": m.group(4), "line": i})
            elif raw[:1].isspace() and factors:
                factors[-1]["detail"] += " " + line.strip()
            else:
                problems.append(("I09", i, f"not a factor line: {line.strip()[:70]!r}"))
    return Log(fields, entries, factors, problems)


def verify(log: Log):
    """(errors, warnings) — each a (code, line, message)."""
    errors, warnings = list(log.problems), []
    f = log.fields
    for req in ("severity", "detected by"):
        if not f.get(req):
            errors.append(("I01", 0, f"header has no **{req.capitalize()}:** field"))
    if not log.entries:
        return errors, warnings
    if log.entries[0].kind != "detected":
        errors.append(("I04", log.entries[0].line, "the first entry must be `detected`"))

    last_time, phase_idx, prod_cleared = None, -1, False
    seen = {}
    for e in log.entries:
        if e.kind not in KINDS:
            errors.append(("I03", e.line, f"unknown kind {e.kind!r}"))
            continue
        if e.kind not in BACKFILL:
            if last_time and e.at < last_time:
                errors.append(("I05", e.line, f"{iso(e.at)} is earlier than the entry before it ({iso(last_time)})"))
            last_time = e.at if not last_time or e.at > last_time else last_time
        if e.kind == "phase":
            name = e.text.split()[0].lower() if e.text.split() else ""
            if name not in PHASES:
                errors.append(("I06", e.line, f"unknown phase {name!r}"))
            elif PHASES.index(name) < phase_idx:
                errors.append(("I06", e.line, f"phase {name} after {PHASES[phase_idx]}"))
            else:
                phase_idx = PHASES.index(name)
        if e.kind == "confirmed":
            prod_cleared = True
        if e.kind == "action[prod]":
            if not prod_cleared:
                errors.append(("I07", e.line, "production action with no `confirmed` entry of its own before it"))
            prod_cleared = False
        if e.kind in MILESTONES:
            if e.kind in seen:
                errors.append(("I08", e.line, f"`{e.kind}` logged twice"))
            for earlier in MILESTONES[:MILESTONES.index(e.kind)]:
                if earlier not in seen:
                    errors.append(("I08", e.line, f"`{e.kind}` before `{earlier}`"))
            seen[e.kind] = e

    if "closed" in seen:
        if not log.factors:
            errors.append(("I09", seen["closed"].line, "closed with no contributing factors recorded"))
        for fac in log.factors:
            d = fac["detail"]
            if fac["outcome"] == "follow-up" and not (re.search(r"\bowner\b", d, re.I) and re.search(r"\bdue\b", d, re.I)):
                errors.append(("I09", fac["line"], f"{fac['id']} follow-up needs an owner and a due date"))
            if fac["outcome"] == "accepted risk" and not re.search(r"\baccepted by\b", d, re.I):
                errors.append(("I09", fac["line"], f"{fac['id']} accepted risk needs who accepted it"))
        if human_detected(f.get("detected by", "")) and not any(
                DETECTION_FIX.search(fac["factor"] + " " + fac["detail"]) for fac in log.factors):
            errors.append(("I10", seen["closed"].line, "a person detected this, and no factor addresses the missing "
                                                      "alert or monitoring"))
        if f.get("status", "").lower() not in ("closed", "resolved"):
            warnings.append(("W02", 0, "header **Status:** still says open"))
    elif "mitigated" not in seen:
        warnings.append(("W01", 0, "not yet mitigated"))
    return errors, warnings


def human_detected(source):
    """True when the detection source names a person and no alerting — judged on the part before the dash."""
    how = source.split("—")[0]
    return bool(USER_DETECTED.search(how)) and not DETECTION_FIX.search(how)


def fmt(p):
    code, line, msg = p
    return f"{code} {'line ' + str(line) if line else 'header'}: {msg}"


# ------------------------------------------------------------------ writing

def insert_in_section(text, section, line):
    """Append `line` at the end of `## section`, creating the section if needed."""
    lines = text.rstrip("\n").splitlines()
    start = next((i for i, l in enumerate(lines) if l.strip().lower() == f"## {section}".lower()), None)
    if start is None:
        return "\n".join(lines) + f"\n\n## {section}\n{line}\n"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    lines.insert(end, line)
    return "\n".join(lines) + "\n"


def cmd_new(a):
    path = pathlib.Path(a.log)
    if path.exists():
        raise Refused(f"{path} already exists — an incident log is never started twice")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Incident: {a.title}\n"
        f"- **Severity:** {a.severity} — {a.why}\n"
        f"- **Detected by:** {a.detected_by}\n"
        f"- **Tracker:** {a.tracker or 'none — this log is the record'}\n"
        f"- **Status:** open\n\n"
        f"## Log\n- {iso(now())} · detected · {a.detected_by}\n\n"
        f"## Contributing factors\n")
    print(path)


def cmd_log(a):
    path = pathlib.Path(a.log)
    text = path.read_text()
    kind, body = a.kind, " ".join(a.text).strip()
    if kind not in KINDS:
        raise Refused(f"unknown kind {kind!r}; one of: {', '.join(KINDS)}")
    if a.at and kind not in BACKFILL:
        raise Refused("only impact-start and change take --at; every other entry is stamped from the clock")
    at = parse_time(a.at) if a.at else now()
    log = parse(text)
    if kind == "action[prod]":
        cleared = False
        for e in log.entries:
            cleared = True if e.kind == "confirmed" else False if e.kind == "action[prod]" else cleared
        if not cleared:
            raise Refused("no confirmation for this production action. Log `proposed`, get the user's explicit "
                          "approval, log `confirmed`, then the action — one approval per action")
    if kind == "closed":
        trial = parse(insert_in_section(text, "Log", f"- {iso(at)} · closed · {body}"))
        errs, _ = verify(trial)
        if errs:
            raise Refused("the incident can't close yet:\n  " + "\n  ".join(fmt(e) for e in errs))
    path.write_text(insert_in_section(text, "Log", f"- {iso(at)} · {kind} · {body}"))
    print(f"{iso(at)} · {kind}")


def cmd_factor(a):
    path = pathlib.Path(a.log)
    text = path.read_text()
    n = max([int(f["id"][1:]) for f in parse(text).factors] or [0]) + 1
    if a.follow_up:
        if not (a.owner and a.due):
            raise Refused("a follow-up needs --owner and --due")
        detail = f"follow-up: {a.follow_up} — owner {a.owner}, due {a.due}" + (f", {a.where}" if a.where else "")
    elif a.accepted:
        if not a.by:
            raise Refused("an accepted risk needs --by (who accepted it)")
        detail = f"accepted risk: {a.accepted} — accepted by {a.by} on {now():%Y-%m-%d}" + (
            f", revisit {a.revisit}" if a.revisit else "")
    else:
        raise Refused("every factor gets --follow-up or --accepted; 'noted' is not an outcome")
    path.write_text(insert_in_section(text, "Contributing factors", f"- **C{n}** {a.factor} → {detail}"))
    print(f"C{n}")


def cmd_check(a):
    log = parse(pathlib.Path(a.log).read_text())
    errors, warnings = verify(log)
    if a.json:
        print(json.dumps({"errors": [fmt(e) for e in errors], "warnings": [fmt(w) for w in warnings]}, indent=2))
    else:
        for w in warnings:
            print("warning:", fmt(w))
        for e in errors:
            print("error:", fmt(e))
        print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def cmd_timeline(a):
    log = parse(pathlib.Path(a.log).read_text())
    first = {}
    for e in log.entries:
        first.setdefault(e.kind, e.at)
    print(f"# Timeline — {pathlib.Path(a.log).stem} (UTC)\n")
    print("| Time | Kind | Event |\n|---|---|---|")
    for e in sorted(log.entries, key=lambda e: e.at):
        print(f"| {iso(e.at)} | {e.kind} | {e.text} |")

    def span(a_, b_):
        if a_ in first and b_ in first:
            mins = (first[b_] - first[a_]).total_seconds() / 60
            return f"{mins:.0f} min"
        return "unknown"
    print(f"\n- **Time to detect** (impact-start → detected): {span('impact-start', 'detected')}")
    print(f"- **Time to mitigate** (detected → mitigated): {span('detected', 'mitigated')}")
    print(f"- **Time to resolve** (detected → resolved): {span('detected', 'resolved')}")
    print(f"- **Production actions:** {sum(1 for e in log.entries if e.kind == 'action[prod]')}, "
          f"each after its own confirmation" if not any(p[0] == "I07" for p in verify(log)[0]) else
          "- **Production actions:** at least one without its own confirmation — see `check`")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("log")
    n.add_argument("--title", required=True)
    n.add_argument("--severity", required=True)
    n.add_argument("--why", required=True)
    n.add_argument("--detected-by", required=True)
    n.add_argument("--tracker")
    lg = sub.add_parser("log")
    lg.add_argument("log")
    lg.add_argument("kind")
    lg.add_argument("text", nargs="+")
    lg.add_argument("--at")
    fc = sub.add_parser("factor")
    fc.add_argument("log")
    fc.add_argument("factor")
    fc.add_argument("--follow-up")
    fc.add_argument("--owner")
    fc.add_argument("--due")
    fc.add_argument("--where")
    fc.add_argument("--accepted")
    fc.add_argument("--by")
    fc.add_argument("--revisit")
    ck = sub.add_parser("check")
    ck.add_argument("log")
    ck.add_argument("--json", action="store_true")
    tl = sub.add_parser("timeline")
    tl.add_argument("log")
    a = ap.parse_args(argv)
    try:
        return {"new": cmd_new, "log": cmd_log, "factor": cmd_factor,
                "check": cmd_check, "timeline": cmd_timeline}[a.cmd](a) or 0
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    except (FileNotFoundError, ValueError) as e:
        print(f"incident: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
