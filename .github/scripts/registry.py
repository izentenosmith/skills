#!/usr/bin/env python3
"""Generate the skill registry from what the repo already records.

    python3 .github/scripts/registry.py            # rewrite skills/REGISTRY.md and skills/registry.json
    python3 .github/scripts/registry.py --check    # exit 1 if either is stale (check_repo.py, CI)

Every field is derived, never typed in, so the registry cannot drift from its
sources without --check failing:

  name, family   the SKILL.md frontmatter `name`; the folder under skills/
  purpose        the first sentence of the frontmatter `description`
  owner          the last matching line of CODEOWNERS (.github/, root or docs/),
                 else DEFAULT_OWNER
  version        the top released `## [X.Y.Z] - YYYY-MM-DD` heading of
                 CHANGELOG.md, else "unreleased": skills are versioned with the repo
  dependencies   only what is known for certain: files copied in from another
                 skill or from harness/ through skills/shared.json, scripts the
                 skill folder carries, and harness/ when evals/scores.json says a
                 scored run staged the skill with it
  last eval      from evals/scores.json: the latest `date` among the skill's
                 evals, and each eval's with-skill delta and capability means

Standard library only. Pass --root to run it against another tree (the tests do).
"""
import argparse
import fnmatch
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_OWNER = "izentenosmith"  # the repo owner; no skill names an owner of its own
OUTPUTS = ("skills/REGISTRY.md", "skills/registry.json")
SCRIPT_SUFFIXES = {".py", ".sh", ".js", ".mjs", ".ts", ".rb", ".pl"}
REGENERATE = "python3 .github/scripts/registry.py"

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
RELEASE = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}\s*$", re.M)
SENTENCE_END = re.compile(r"[.!?](?=\s+[A-Z\"'`(]|\s*$)")


def scalar(raw):
    """A one-line YAML scalar's value (check_repo.py rejects the forms this can't read)."""
    raw = raw.strip()
    if raw[:1] == '"' and raw[-1:] == '"':
        return re.sub(r"\\(.)", r"\1", raw[1:-1])
    if raw[:1] == "'" and raw[-1:] == "'":
        return raw[1:-1].replace("''", "'")
    return raw


def first_sentence(text):
    m = SENTENCE_END.search(text)
    return text[:m.end()] if m else text


def version(root):
    changelog = root / "CHANGELOG.md"
    if changelog.is_file():
        m = RELEASE.search(changelog.read_text())
        if m:
            return m.group(1)
    return "unreleased"


def codeowners(root):
    """(pattern, owners) in file order, from the first CODEOWNERS GitHub would read."""
    for rel in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        p = root / rel
        if p.is_file():
            rules = []
            for line in p.read_text().splitlines():
                line = line.split("#", 1)[0].split()
                if len(line) >= 2:
                    rules.append((line[0], [o.lstrip("@") for o in line[1:]]))
            return rules
    return []


def owns(pattern, path):
    """Whether a CODEOWNERS pattern covers a repo-relative folder path (a subset
    of gitignore syntax: anchored /x, folder x/, globs, ** prefixes)."""
    anchored = pattern.startswith("/") or "/" in pattern.rstrip("/")
    pat = pattern.strip("/")
    if pat in ("*", "**"):
        return True
    parts = path.split("/")
    prefixes = ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]
    if anchored:
        pat = pat.removeprefix("**/")
        return any(fnmatch.fnmatchcase(p, pat) for p in prefixes)
    return any(fnmatch.fnmatchcase(seg, pat) for seg in parts)


def owner(rules, path):
    found = None
    for pattern, owners in rules:
        if owns(pattern, path):
            found = owners  # the last matching line wins
    return ", ".join(found) if found else DEFAULT_OWNER


def source_label(source):
    parts = pathlib.PurePosixPath(source).parts
    return parts[2] if parts[0] == "skills" and len(parts) > 3 else parts[0] + "/"


def build(root):
    """One dict per skill, sorted by family then name."""
    shared = {}
    manifest = root / "skills/shared.json"
    if manifest.is_file():
        for source, copies in json.loads(manifest.read_text()).items():
            for copy in copies:
                shared[copy] = source
    scores_path = root / "evals/scores.json"
    scores = json.loads(scores_path.read_text())["evals"] if scores_path.is_file() else {}
    rules = codeowners(root)
    out = []
    for md in sorted((root / "skills").glob("*/*/SKILL.md")):
        m = FRONTMATTER.match(md.read_text())
        if not m:
            continue
        fields = dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M))
        name, desc = scalar(fields.get("name", "")), scalar(fields.get("description", ""))
        if not name:
            continue
        folder = md.parent
        rel = folder.relative_to(root).as_posix()
        copies = {}
        scripts = []
        for f in sorted(p for p in folder.rglob("*") if p.is_file()):
            frel = f.relative_to(root).as_posix()
            inner = f.relative_to(folder).as_posix()
            if "__pycache__" in f.parts:
                continue
            if frel in shared:
                copies.setdefault(source_label(shared[frel]), []).append(inner)
            elif f.suffix in SCRIPT_SUFFIXES:
                scripts.append(inner)
        evals = sorted(({"eval": e, "id": int(e.split("-")[1]), **{k: s.get(k) for k in (
                         "iteration", "n", "date", "delta_mean", "cap_mean", "staging")}}
                        for e, s in scores.items() if s.get("skill") == name),
                       key=lambda e: e["id"])
        dates = [e["date"] for e in evals if e["date"]]
        out.append({
            "name": name, "family": folder.parent.name, "path": f"{rel}/SKILL.md",
            "purpose": first_sentence(desc), "owner": owner(rules, rel),
            "dependencies": {"copied_from": copies, "scripts": scripts,
                             "harness": any(e["staging"] == "harness" for e in evals)},
            "last_eval": max(dates) if dates else None,
            "evals": [{k: v for k, v in e.items() if k != "staging"} for e in evals],
        })
    out.sort(key=lambda s: (s["family"], s["name"]))
    return out


def deps_text(d):
    parts = [f"copies from {src}: {', '.join(files)}" for src, files in sorted(d["copied_from"].items())]
    if d["scripts"]:
        parts.append(f"scripts: {', '.join(d['scripts'])}")
    if d["harness"]:
        parts.append("harness/ (scored with it)")
    return "; ".join(parts) or "—"


def render(root):
    """{output path: text} for both registry files."""
    skills, ver = build(root), version(root)
    num = lambda v: "—" if v is None else f"{v:.2f}"
    cell = lambda s: s.replace("|", "\\|")
    L = ["# Skill registry", "",
         f"Generated by `.github/scripts/registry.py` from each `SKILL.md`'s frontmatter, "
         f"`skills/shared.json`, `evals/scores.json` and `CHANGELOG.md`. Do not edit it by hand: "
         f"run `{REGENERATE}`. CI fails when it is stale.", "",
         f"Skills are versioned with the repo, not one by one: every skill is at the repo's release "
         f"version, the top released heading of `CHANGELOG.md` (`unreleased` when there is none). "
         f"Purpose is the description's first sentence. Owner comes from `CODEOWNERS`, else the repo "
         f"owner. Dependencies list only what is certain: files copied in from another skill or from "
         f"`harness/` (see `skills/shared.json`), scripts the skill carries, and `harness/` when a "
         f"scored run staged the skill beside it. Last eval is the UTC day the latest scored "
         f"with-skill run ended; each eval shows its with-skill delta and capability means (see "
         f"[evals/benchmark.md](../evals/benchmark.md) for baselines and noise).", "",
         f"{len(skills)} skills, version {ver}.", "",
         "| Skill | Family | Purpose | Owner | Version | Dependencies | Last eval | Eval scores (delta / cap) |",
         "|---|---|---|---|---|---|---|---|"]
    for s in skills:
        link = s["path"].removeprefix("skills/")
        scores = "<br>".join(f"{e['id']}: {num(e['delta_mean'])} / {num(e['cap_mean'])}"
                             for e in s["evals"]) or "—"
        L.append(f"| [{s['name']}]({link}) | {s['family']} | {cell(s['purpose'])} | {s['owner']} "
                 f"| {ver} | {cell(deps_text(s['dependencies']))} | {s['last_eval'] or '—'} | {scores} |")
    data = {"note": f"Generated by .github/scripts/registry.py; regenerate with {REGENERATE}.",
            "version": ver, "skills": skills}
    return {OUTPUTS[0]: "\n".join(L) + "\n", OUTPUTS[1]: json.dumps(data, indent=2) + "\n"}


def stale(root=ROOT):
    """A message for each registry file that differs from what would be generated."""
    out = []
    for rel, text in render(root).items():
        p = root / rel
        if not p.is_file() or p.read_text() != text:
            out.append(f"{rel}: stale — regenerate it with {REGENERATE}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if the registry is stale")
    ap.add_argument("--root", type=pathlib.Path, default=ROOT, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.check:
        msgs = stale(args.root)
        for m in msgs:
            print(m)
        return 1 if msgs else 0
    for rel, text in render(args.root).items():
        (args.root / rel).write_text(text)
        print(f"wrote {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
