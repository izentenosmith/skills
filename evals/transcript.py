#!/usr/bin/env python3
"""Read what a run did, and why its grade is what it is.

Usage: python3 transcript.py <run-dir>              one run, turn by turn
       python3 transcript.py --failures <iter-dir>  every failed assertion in an iteration

A run directory is <iteration>/eval-<id>-<name>/with_skill/repK or .../old_skill.
The first form prints the run's grade, then every message, tool call and tool
result from the transcript.jsonl run.py keeps. The second lists each failed
assertion with the grader's evidence and the run to open next. A score means
little until someone has read the runs behind it: a failure is either the
skill's, the task's or the grader's, and only the transcript says which.
"""
import argparse
import json
import pathlib
import sys

WIDTH = 600  # characters shown of one tool input or result; --full lifts it


def load(p):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def clip(text, full):
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    return text if full or len(text) <= WIDTH else f"{text[:WIDTH]} … [{len(text) - WIDTH} more characters]"


def events(run):
    for line in (run / "transcript.jsonl").read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(ev, dict):
            yield ev


def steps(run):
    """(kind, text) for every text block, tool call and tool result, in order."""
    for ev in events(run):
        content = (ev.get("message") or {}).get("content") if ev.get("type") in ("assistant", "user") else None
        for b in content if isinstance(content, list) else []:
            if b.get("type") == "text":
                yield "says", b.get("text", "")
            elif b.get("type") == "tool_use":
                yield f"calls {b.get('name')}", b.get("input", {})
            elif b.get("type") == "tool_result":
                c = b.get("content")
                if isinstance(c, list):
                    c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
                yield "error" if b.get("is_error") else "result", c or ""


def tool_calls(run):
    """[(tool name, input)] the run made, for a grader that needs to know what
    a run did rather than what it says it did. [] when there is no transcript."""
    if not (run / "transcript.jsonl").exists():
        return []
    return [(b.get("name"), b.get("input", {}))
            for ev in events(run) if ev.get("type") == "assistant"
            for b in (ev.get("message") or {}).get("content") or []
            if isinstance(b, dict) and b.get("type") == "tool_use"]


def show_run(run, full):
    rec, grading = load(run / "run.json") or {}, load(run / "grading.json")
    print(f"# {run}")
    print(f"ok={rec.get('ok')} timed_out={rec.get('timed_out')} response={rec.get('response')!r} "
          f"turns={rec.get('num_turns')} cost=${rec.get('cost_usd') or 0:.2f} seconds={rec.get('seconds')}")
    if grading:
        print(f"\n## Grade: {grading['passed']}/{grading['total']}, delta "
              f"{grading['delta_passed']}/{grading['delta_total']}")
        for e in grading["expectations"]:
            if not e["passed"]:
                print(f"- FAILED [{e['kind']}] {e['text']}" + (f" — {e['evidence']}" if e["evidence"] else ""))
    print("\n## Transcript")
    if not (run / "transcript.jsonl").exists():
        print("No transcript.jsonl: this run predates the transcripts run.py keeps. "
              f"Its final response is {run / 'outputs/response.md'}.")
        return
    for n, (kind, text) in enumerate(steps(run), 1):
        print(f"\n[{n}] {kind}\n{clip(text, full)}")


def show_failures(it):
    """Every failed assertion, grouped by eval, so the misses can be sorted by
    cause before anything is edited."""
    total = 0
    for ed in sorted(p for p in it.iterdir() if p.is_dir() and p.name.startswith("eval-")):
        rows = []
        for g in sorted(ed.glob("with_skill/rep[0-9]*/grading.json")):
            rows += [(g.parent, e) for e in (load(g) or {}).get("expectations", []) if not e["passed"]]
        lost = [p.parent for p in sorted(ed.glob("with_skill/rep[0-9]*/run.json"))
                if not (p.parent / "grading.json").exists()]
        if not rows and not lost:
            continue
        print(f"\n## {ed.name}")
        for run in lost:
            rec = load(run / "run.json") or {}
            print(f"- NOT GRADED {run.name}: timed_out={rec.get('timed_out')} "
                  f"exit={rec.get('exit_code')} response={rec.get('response')!r}\n  {run}")
        for run, e in rows:
            total += 1
            print(f"- [{e['kind']}] {e['text']} ({run.name})"
                  + (f"\n  evidence: {e['evidence']}" if e["evidence"] else "") + f"\n  {run}")
    print(f"\n{total} failed assertion(s) in with-skill runs. Read each run before changing a skill "
          "or a grader: python3 transcript.py <run-dir>")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("path", type=pathlib.Path, help="a run directory, or an iteration with --failures")
    ap.add_argument("--failures", action="store_true", help="list every failed assertion in an iteration")
    ap.add_argument("--full", action="store_true", help="do not shorten tool inputs and results")
    args = ap.parse_args()
    if not args.path.is_dir():
        sys.exit(f"{args.path} is not a directory")
    if args.failures:
        show_failures(args.path)
    else:
        show_run(args.path, args.full)


if __name__ == "__main__":
    main()
