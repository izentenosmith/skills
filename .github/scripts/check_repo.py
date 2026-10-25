#!/usr/bin/env python3
"""Structural checks for this repo: the things a skill install or an eval run
breaks on, and that no test exercises.

    python3 .github/scripts/check_repo.py      # exit 0 clean · 1 problems found

Skills
  - every SKILL.md has frontmatter with `name` and `description`
  - `name` equals the folder name (the CLI installs by name) and is unique
  - `description` fits the 1024-character limit agents load
  - every symlink under skills/ resolves (installs dereference them)
  - the root README links every skill
Links
  - every relative link in a tracked markdown file resolves, outside code
    spans and fences; eval fixtures are skipped (their content is planted)
Evals
  - evals.json parses, ids are unique, and each eval names a skill that exists
    (or the loop runner) and a fixture folder that exists
  - grade.py has a check for every eval and no check without an eval
  - every control in make_controls.py grades an eval that exists
  - no answer key sits inside a fixture folder (runs copy the folder)
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVALS = ROOT / "evals"
problems = []


def problem(msg):
    problems.append(msg)


def tracked(*patterns):
    out = subprocess.run(["git", "ls-files", "-z", "--", *patterns], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    return [ROOT / p for p in out.split("\0") if p]


# ---------------------------------------------------------------- skills

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
skills = {}
for md in tracked("skills/**/SKILL.md"):
    rel = md.relative_to(ROOT)
    m = FRONTMATTER.match(md.read_text())
    if not m:
        problem(f"{rel}: no YAML frontmatter")
        continue
    fields = dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M))
    name, desc = fields.get("name", "").strip(), fields.get("description", "").strip()
    if not name or not desc:
        problem(f"{rel}: frontmatter needs both name and description")
        continue
    if name != md.parent.name:
        problem(f"{rel}: name {name!r} does not match its folder {md.parent.name!r}")
    if len(desc) > 1024:
        problem(f"{rel}: description is {len(desc)} characters (limit 1024)")
    if name in skills:
        problem(f"{rel}: name {name!r} is also used by {skills[name]}")
    skills[name] = rel

for link in (ROOT / "skills").rglob("*"):
    if link.is_symlink() and not link.exists():
        problem(f"{link.relative_to(ROOT)}: broken symlink -> {link.readlink()}")

readme = (ROOT / "README.md").read_text()
for name, rel in sorted(skills.items()):
    if f"({rel})" not in readme:
        problem(f"README.md: no link to {rel}")

# ----------------------------------------------------------------- links

FENCE = re.compile(r"^(```|~~~).*?^\1", re.S | re.M)
CODE = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"\]\(([^)\s]+)\)")
for md in tracked("*.md"):
    rel = md.relative_to(ROOT)
    if rel.parts[:2] == ("evals", "fixtures"):
        continue
    text = CODE.sub("", FENCE.sub("", md.read_text()))
    for target in LINK.findall(text):
        if re.match(r"[a-z][a-z0-9+.-]*:|#", target):
            continue
        path = target.split("#", 1)[0]
        if path and not (md.parent / path).exists():
            problem(f"{rel}: broken link ({target})")

# ----------------------------------------------------------------- evals

sys.path.insert(0, str(EVALS))
sys.path.insert(0, str(EVALS / "controls"))
import grade  # noqa: E402
import make_controls  # noqa: E402

data = json.loads((EVALS / "evals.json").read_text())
seen, names = set(), set()
for ev in data["evals"]:
    eid, name = ev["id"], f"eval-{ev['id']}-{ev['name']}"
    if eid in seen:
        problem(f"evals.json: duplicate id {eid}")
    seen.add(eid)
    names.add(name)
    if ev.get("runner") != "loop" and ev["skill"] not in skills:
        problem(f"evals.json: eval {eid} names skill {ev['skill']!r}, which no SKILL.md defines")
    fixture = ev["fixture"]
    fixture = "base" if fixture == "fixture" else fixture.removeprefix("fixture-")
    if not (EVALS / "fixtures" / fixture).is_dir():
        problem(f"evals.json: eval {eid} names fixture {ev['fixture']!r}, which does not exist")
    if name not in grade.CHECKS:
        problem(f"grade.py: no check for {name}")
for name in sorted(set(grade.CHECKS) - names):
    problem(f"grade.py: check {name} has no eval in evals.json")
for name in sorted(set(make_controls.CONTROLS) - set(grade.CHECKS)):
    problem(f"make_controls.py: controls for {name}, which grade.py does not check")

for key in tracked("evals/fixtures/*/*.answers.md", "evals/fixtures/*/**/*.answers.md"):
    problem(f"{key.relative_to(ROOT)}: answer key inside a fixture folder — runs copy the folder")

# ---------------------------------------------------------------- report

for p in problems:
    print(f"✗ {p}")
print(f"{len(skills)} skills, {len(data['evals'])} evals, {len(problems)} problem(s)")
sys.exit(1 if problems else 0)
