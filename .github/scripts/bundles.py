"""Check skills/bundles.json, the role-based bundles, against the skills that
exist and against the install lines README.md shows for them.

check_repo.py calls check(); it lives here so evals/tests/test_bundles.py can
test it without running every other repo check.
"""
import json
import re

LIMIT = 20  # skills per install line, the bundle's extras included
INSTALL = "npx skills add izentenosmith/skills --skill "


def readme_lines(readme_text):
    """{bundle: [skill, ...]} from the first code block under README.md's
    `### Bundles` (None without the section): each `# <name>` comment names the
    bundle of the install line that follows it."""
    text = readme_text.splitlines()
    try:
        start = [t.strip() for t in text].index("### Bundles")
    except ValueError:
        return None
    lines, name, fenced = {}, None, False
    for line in text[start + 1:]:
        line = line.strip()
        if line.startswith("```"):
            if fenced:
                break  # only the first block holds the bundles
            fenced = True
            continue
        if not fenced:
            if re.match(r"#{1,6} ", line):
                break  # the next heading ends the section
            continue
        if c := re.fullmatch(r"#\s*([\w-]+)\b.*", line):
            name = c.group(1)
        elif line.startswith(INSTALL):
            key = name if name is not None else "(no comment)"
            lines[key] = line[len(INSTALL):].split()
            name = None
    return lines


def check(manifest, skill_names, readme_text):
    """Problems with the bundles manifest (its text, or a parsed dict), given the
    names of the skills that exist and the root README's text."""
    out = []
    if isinstance(manifest, str):
        try:
            manifest = json.loads(manifest)
        except ValueError as e:
            return [f"skills/bundles.json: does not parse ({e})"]
    skill_names = set(skill_names)
    bundles = manifest.get("bundles") if isinstance(manifest, dict) else None
    if not isinstance(bundles, dict) or not bundles:
        return ["skills/bundles.json: no bundles"]
    extras = manifest.get("with_every_bundle", [])
    for name in extras:
        if name not in skill_names:
            out.append(f"skills/bundles.json: with_every_bundle names {name!r}, which no SKILL.md defines")

    covered = set(extras)
    for bundle, spec in bundles.items():
        where = f"skills/bundles.json: bundle {bundle!r}"
        skills = spec.get("skills") if isinstance(spec, dict) else None
        if not skills:
            out.append(f"{where} has no skills")
            continue
        for name in sorted({s for s in skills if skills.count(s) > 1}):
            out.append(f"{where} lists {name!r} more than once")
        for name in skills:
            if name not in skill_names:
                out.append(f"{where} names {name!r}, which no SKILL.md defines")
        covered |= set(skills)
        line = list(dict.fromkeys(skills + extras))
        if len(line) > LIMIT:
            out.append(f"{where} installs {len(line)} skills with {', '.join(extras)} (limit {LIMIT})")
        for name in spec.get("placed", {}):
            if name not in skills:
                out.append(f"{where} gives a placed reason for {name!r}, which it does not list")
    for name in sorted(skill_names - covered):
        out.append(f"skills/bundles.json: {name} is in no bundle")

    lines = readme_lines(readme_text)
    if lines is None:
        return out + ["README.md: no `### Bundles` section with an install line per bundle"]
    for bundle, spec in bundles.items():
        skills = spec.get("skills") if isinstance(spec, dict) else None
        if not skills:
            continue
        if bundle not in lines:
            out.append(f"README.md: Bundles has no `# {bundle}` comment followed by its install line")
            continue
        want = list(dict.fromkeys(skills + extras))
        if set(lines[bundle]) != set(want) or len(lines[bundle]) != len(want):
            out.append(f"README.md: the {bundle} install line installs {' '.join(lines[bundle])}; "
                       f"skills/bundles.json says {' '.join(want)}")
    for bundle in lines:
        if bundle not in bundles:
            out.append(f"README.md: Bundles has an install line for {bundle!r}, which skills/bundles.json "
                       f"does not define")
    return out
