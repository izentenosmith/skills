"""Authoring-guide checks for skill folders, after Anthropic's skill authoring
best practices. check_repo.py runs them on the families in GUIDED_FAMILIES;
each function takes text, not paths, so evals/tests/test_authoring.py can test
them without the repo.

  1. the description is written in the third person ("Turns…", "Adjudicates…")
  2. a reference file over 100 lines opens with a `## Contents` list of its sections
  3. SKILL.md lists every reference file under `## Reference files`, each with a
     "when to open it" line, and no reference file links to another one
  4. no link leaves the skill's own folder: installs are one folder per skill
"""
import re

GUIDED_FAMILIES = ("development",)
TOC_THRESHOLD = 100

FENCE = re.compile(r"^(```|~~~).*?^\1", re.S | re.M)
CODE = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"\]\(([^)\s]+)\)")


def slug(heading):
    """GitHub's anchor for a heading."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def h2_headings(text):
    return re.findall(r"^## (.+?)\s*$", FENCE.sub("", text), re.M)


def section(text, title):
    """The body of the `## <title>` section (outside fences), or None."""
    text = FENCE.sub("", text)
    m = re.search(rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def links(text):
    """Relative link targets outside code, minus external and in-page ones."""
    text = CODE.sub("", FENCE.sub("", text))
    return [t for t in LINK.findall(text) if not re.match(r"[a-z][a-z0-9+.-]*:|#", t)]


def description_problems(desc):
    first = desc.split()[0] if desc.split() else ""
    out = []
    if not re.fullmatch(r"[A-Z][a-z]+(?:-[a-z]+)*s", first) or first in ("Use", "Uses"):
        out.append(f"description should open with a third-person verb (\"Turns…\", \"Runs…\"), not {first!r}")
    if m := re.search(r"\b(?:[Yy]ou|[Yy]our|[Yy]ours|I)\b", desc):
        out.append(f"description should be third person; it says {m.group(0)!r}")
    return out


def toc_problems(text):
    """A long reference file needs `## Contents` linking every other `##` section."""
    if len(text.splitlines()) <= TOC_THRESHOLD:
        return []
    body = section(text, "Contents")
    if body is None:
        return [f"over {TOC_THRESHOLD} lines with no `## Contents` list of its sections"]
    listed = re.findall(r"^\s*[-*] \[[^\]]+\]\(#([^)]+)\)", body, re.M)
    wanted = [slug(h) for h in h2_headings(text) if h != "Contents"]
    out = [f"`## Contents` does not list section #{a}" for a in wanted if a not in listed]
    out += [f"`## Contents` links #{a}, which is no `##` section" for a in listed if a not in wanted]
    return out


def reference_index_problems(skill_text, reference_names):
    """SKILL.md's `## Reference files` names each reference with when to open it."""
    if not reference_names:
        return []
    body = section(skill_text, "Reference files")
    if body is None:
        return ["no `## Reference files` section listing the reference files"]
    out = []
    for name in sorted(reference_names):
        lines = [ln for ln in body.splitlines() if f"]({name})" in ln]
        if not lines:
            out.append(f"`## Reference files` does not list {name}")
        elif not any(re.search(r"\bwhen\b", ln, re.I) for ln in lines):
            out.append(f"`## Reference files` lists {name} without saying when to open it")
    return out


def reference_link_problems(text, reference_names):
    """A reference file may link SKILL.md, never another reference file."""
    return [f"links {t}; references stay one level deep, so name `{t.split('#')[0]}` in backticks instead"
            for t in links(text) if t.split("#", 1)[0] in reference_names]


def escaping_link_problems(text, folder, here):
    """Links in a file at `here` (a Path inside skill `folder`) must stay in the folder."""
    out = []
    for t in links(text):
        path = t.split("#", 1)[0]
        if path and not (here.parent / path).resolve().is_relative_to(folder.resolve()):
            out.append(f"link {t} leaves the skill folder, so it is dead once the skill is installed "
                       f"alone; name the skill in backticks instead")
    return out


def check_skill(folder):
    """Every authoring-guide problem in one skill folder, as (relative file, message)."""
    skill_md = folder / "SKILL.md"
    skill_text = skill_md.read_text()
    out = []
    fm = re.match(r"\A---\n(.*?)\n---\n", skill_text, re.S)
    if fm and (m := re.search(r"^description:\s*(.*)$", fm.group(1), re.M)):
        desc = m.group(1).strip()
        if desc[:1] in "\"'":
            desc = desc[1:-1].replace('\\"', '"')
        out += [("SKILL.md", p) for p in description_problems(desc)]
    refs = {p.name: p for p in folder.glob("*.md") if p.name != "SKILL.md"}
    out += [("SKILL.md", p) for p in reference_index_problems(skill_text, set(refs))]
    out += [("SKILL.md", p) for p in escaping_link_problems(skill_text, folder, skill_md)]
    for name, path in sorted(refs.items()):
        text = path.read_text()
        out += [(name, p) for p in toc_problems(text)]
        out += [(name, p) for p in reference_link_problems(text, set(refs) - {name})]
        out += [(name, p) for p in escaping_link_problems(text, folder, path)]
    return out
