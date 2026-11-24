#!/usr/bin/env python3
"""Structural checks for this repo: the things a skill install or an eval run
breaks on, and that no test exercises.

    python3 .github/scripts/check_repo.py            # exit 0 clean · 1 problems found
    python3 .github/scripts/check_repo.py --strict   # warnings count as problems

Skills
  - every SKILL.md has frontmatter with `name` and `description`
  - `name` equals the folder name (the CLI installs by name) and is unique
  - `name` and `description` parse as YAML scalars (an unquoted `: ` or ` #`
    gets a skill skipped or its description cut) and the description fits
    the 500-character budget (authoring.DESCRIPTION_BUDGET, all families;
    agents cut at 1024)
  - no symlinks under skills/ (`npx skills add` drops a link that leaves the
    skill folder); every copy in skills/shared.json matches its source
  - the root README links every skill
  - skills/REGISTRY.md and skills/registry.json match what registry.py generates
Links
  - every relative link in a tracked markdown file resolves, outside code
    spans and fences; eval fixtures are skipped (their content is planted)
  - a link inside a skill folder stays within its family: installs are flat,
    so `../../<family>/...` only resolves in this repo
Authoring guide (families in authoring.GUIDED_FAMILIES; details in authoring.py)
  - the description is third person, opening with a verb ("Turns…")
  - a reference file over 100 lines opens with a `## Contents` list
  - SKILL.md lists every reference file under `## Reference files` with when to
    open it, and reference files don't link each other (one level deep)
  - no link leaves the skill's own folder (sibling skills are named, not linked)
Evals
  - evals.json parses, ids are unique, and each eval names a skill that exists
    (or the loop runner) and a fixture folder that exists
  - grade.py has a check for every eval and no check without an eval
  - every control in make_controls.py grades an eval that exists
  - no answer key sits inside a fixture folder (runs copy the folder)
Eval health
  - every skill has at least one eval
  - warning: a skill eval with no score in scores.json
  - warning: a score whose skill_hash differs from the skill as it is now
    (the skill changed since its last scored run), computed the way the run
    staged it (the repo folder, alone or with harness/ beside it)
  - warning: a score with no skill_hash (scored before run.py recorded one),
    or one staged by the zip-packaging step this repo no longer has
Bundles
  - skills/bundles.json parses; every skill it names exists; every skill is
    in at least one bundle; no install line (with the with_every_bundle
    extras) passes 20 skills; no duplicate in a bundle; a `placed` reason
    only for a skill its bundle lists
  - README.md's `### Bundles` has a `# <name>` comment and install line per
    bundle, each installing exactly that bundle's skills plus the extras
Plugin (.claude-plugin/marketplace.json)
  - the marketplace has one plugin, sourced from ./skills with strict false,
    so an install copies the skills and none of harness/ or evals/
  - its `skills` lists exactly the family folders that hold a skill (the
    plugin scan is one level deep, so a family missing here installs none of
    its skills)
  - its `version` is the top released version in CHANGELOG.md
Branch protection
  - every status check .github/rulesets/main.json requires is a job name the
    workflows report — a renamed job would otherwise block every merge
"""
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVALS = ROOT / "evals"
STRICT = "--strict" in sys.argv[1:]
problems, warnings = [], []


def problem(msg):
    problems.append(msg)


def warning(msg):
    """Not broken, but not a score you can trust as current either. --strict fails on it."""
    (problems if STRICT else warnings).append(msg)


def tracked(*patterns):
    out = subprocess.run(["git", "ls-files", "-z", "--", *patterns], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    return [ROOT / p for p in out.split("\0") if p]


# ---------------------------------------------------------------- skills

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)

sys.path.insert(0, str(ROOT / ".github/scripts"))
import authoring  # noqa: E402
from authoring import yaml_scalar  # noqa: E402

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
    bad = False
    for key in ("name", "description"):
        _, why = yaml_scalar(fields[key].strip())
        if why:
            problem(f"{rel}: {key} is {why}; wrap it in double quotes")
            bad = True
    if bad:
        continue
    name, desc = yaml_scalar(name)[0], yaml_scalar(desc)[0]
    if name != md.parent.name:
        problem(f"{rel}: name {name!r} does not match its folder {md.parent.name!r}")
    for msg in authoring.description_length_problems(desc):
        problem(f"{rel}: {msg}")
    if name in skills:
        problem(f"{rel}: name {name!r} is also used by {skills[name]}")
    skills[name] = rel

for link in (ROOT / "skills").rglob("*"):
    if link.is_symlink():
        problem(f"{link.relative_to(ROOT)}: a symlink — `npx skills add` drops links that leave "
                f"the skill folder; list it as a copy in skills/shared.json instead")

import sync_shared  # noqa: E402

for msg in sync_shared.stale():
    problem(msg)

import registry  # noqa: E402

for msg in registry.stale():
    problem(msg)

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
        elif path and rel.parts[0] == "skills" and len(rel.parts) >= 4:
            # Installs are flat (~/.agents/skills/<skill>/), so a link inside a
            # skill only resolves there if it stays within the skill's family.
            family = (ROOT / "skills" / rel.parts[1]).resolve()
            if not (md.parent / path).resolve().is_relative_to(family):
                problem(f"{rel}: link {target} leaves the {rel.parts[1]} family, so it breaks "
                        f"once installed; name the skill in backticks instead")

# -------------------------------------------------------- authoring guide

for name, rel in sorted(skills.items()):
    if rel.parts[1] in authoring.GUIDED_FAMILIES:
        for fname, msg in authoring.check_skill(ROOT / rel.parent):
            problem(f"{rel.parent / fname}: {msg}")

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

# ------------------------------------------------------------ eval health

import run  # noqa: E402

skill_evals = {}
for ev in data["evals"]:
    if ev.get("runner") != "loop":
        skill_evals.setdefault(ev["skill"], []).append(f"eval-{ev['id']}-{ev['name']}")
for name, rel in sorted(skills.items()):
    if name not in skill_evals:
        problem(f"{rel}: no eval in evals/evals.json; every skill needs a scored eval before it ships")

scores = json.loads((EVALS / "scores.json").read_text())["evals"]
current, unscored, unhashed, legacy = {}, [], {}, {}
for name, evs in sorted(skill_evals.items()):
    if name not in skills:
        continue  # reported above
    for ev in evs:
        score = scores.get(ev)
        if score is None:
            unscored.append(ev)
            continue
        if score["skill_hash"] is None:
            unhashed.setdefault(name, []).append(score["iteration"])
            continue
        staging = score["staging"]
        if staging not in ("harness", "standalone"):
            legacy.setdefault(name, []).append(score["iteration"])
            continue
        if (name, staging) not in current:
            try:
                current[name, staging] = run.skill_hash(ROOT / skills[name].parent, staging)
            except ValueError as e:
                current[name, staging] = None
                warning(f"{ev}: can't tell whether its score is current — {e}")
        if current[name, staging] not in (None, score["skill_hash"]):
            warning(f"{ev}: {name} changed since its last scored run ({score['iteration']}, staged as "
                    f"{staging}); re-run it: python3 evals/run.py --evals {ev.split('-')[1]}")
for ev in unscored:
    warning(f"{ev}: no score in evals/scores.json — run it, then aggregate.py --record")
if unhashed:
    warning(f"{len(unhashed)} skill(s) scored before run.py recorded skill hashes, so whether "
            f"they changed since is unknown: {', '.join(sorted(unhashed))}")
if legacy:
    warning(f"{len(legacy)} skill(s) scored through the zip-packaging step this repo no longer has, so whether "
            f"they changed since is unknown until a re-run: {', '.join(sorted(legacy))}")

# --------------------------------------------------- ruleset vs workflow

def job_names(workflow):
    """Display names of the workflow's jobs, matrix values substituted — the
    names GitHub reports as status checks. Stdlib only, so a line-level read
    of the block layout this repo's workflows use."""
    names, job, block = [], None, {}

    def flush():
        if job is None:
            return
        name = block.get("name", job)
        expanded = [name]
        for key, values in block.get("matrix", {}).items():
            expanded = [n.replace(f"${{{{ matrix.{key} }}}}", v) for n in expanded for v in values]
        names.extend(expanded)

    in_jobs = False
    for line in workflow.splitlines():
        if re.match(r"^jobs:\s*$", line):
            in_jobs = True
            continue
        if in_jobs and re.match(r"^\S", line):
            break
        if not in_jobs:
            continue
        if m := re.match(r"^  ([\w-]+):\s*$", line):
            flush()
            job, block = m.group(1), {}
        elif m := re.match(r"^    name:\s*(.+?)\s*$", line):
            block["name"] = m.group(1).strip("\"'")
        elif m := re.match(r"^        ([\w-]+):\s*\[(.*)\]\s*$", line):
            block.setdefault("matrix", {})[m.group(1)] = [v.strip().strip("\"'") for v in m.group(2).split(",")]
    flush()
    return names


ruleset_path = ROOT / ".github/rulesets/main.json"
if ruleset_path.exists():
    ruleset = json.loads(ruleset_path.read_text())
    reported = set()
    for wf in tracked(".github/workflows/*.yml", ".github/workflows/*.yaml"):
        reported |= set(job_names(wf.read_text()))
    for rule in ruleset["rules"]:
        for check in rule.get("parameters", {}).get("required_status_checks", []):
            if check["context"] not in reported:
                problem(f".github/rulesets/main.json: required check {check['context']!r} matches no workflow job "
                        f"— merges into main would wait for it forever (jobs: {sorted(reported)})")

# ---------------------------------------------------------------- plugin

MARKET = ".claude-plugin/marketplace.json"
entries = json.loads((ROOT / MARKET).read_text()).get("plugins", [])
if len(entries) != 1 or entries[0].get("source") != "./skills" or entries[0].get("strict") is not False:
    problem(f"{MARKET}: needs exactly one plugin with \"source\": \"./skills\" and \"strict\": false "
            f"(a root source installs harness/ and evals/ too)")
else:
    entry = entries[0]
    families = sorted({f"./{rel.parts[1]}" for rel in skills.values()})
    if sorted(entry.get("skills", [])) != families:
        problem(f"{MARKET}: skills is {sorted(entry.get('skills', []))}, expected the family folders {families}")
    released = registry.version(ROOT)
    if entry.get("version") != released:
        problem(f"{MARKET}: version {entry.get('version')!r} is not the top released version in "
                f"CHANGELOG.md ({released!r}); a release moves both")
    if (ROOT / ".claude-plugin/plugin.json").exists():
        problem(".claude-plugin/plugin.json: the marketplace entry is the plugin's whole definition "
                "(strict false); a plugin.json beside it would be a second, unchecked one")

# --------------------------------------------------------------- bundles

import bundles  # noqa: E402

for msg in bundles.check((ROOT / "skills/bundles.json").read_text(), skills, readme):
    problem(msg)

# ---------------------------------------------------------------- report

annotate = "GITHUB_ACTIONS" in os.environ
for w in warnings:
    print(f"::warning title=eval health::{w}" if annotate else f"! {w}")
for p in problems:
    print(f"✗ {p}")
print(f"{len(skills)} skills, {len(data['evals'])} evals, {len(problems)} problem(s), {len(warnings)} warning(s)")
sys.exit(1 if problems else 0)
