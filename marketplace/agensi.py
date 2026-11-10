#!/usr/bin/env python3
"""Package skills/ as Agensi-ready zips: one per skill, and one per bundle.

The repo is the source of truth; a zip is a build artefact made from it. Each
skill is packaged so it stands alone when someone installs only that one:

  - symlinked reference docs become real files
  - a link to another skill's reference doc copies that doc into the package
    (and whatever it links to in turn), and the link points at the copy
  - a link to another skill's SKILL.md becomes the skill's name in plain text,
    and SKILL.md gains a short "Related skills" section naming them
  - a link to anything else outside the skill (a family README, the harness)
    becomes its link text
  - patches.json applies exact text edits a generic rule can't make, such as a
    sentence about the harness, and drops whole sections by heading; a patch
    that no longer matches fails the build

A bundle (bundles.json) zips several skill folders side by side. Links between
its members stay live, as ../<member>/<file>; links to anything outside the
bundle get the same treatment as above.

A single skill lists at SKILL_PRICE_USD ($5) and a bundle at BUNDLE_PRICE_USD
($10), however many skills it holds. Then each listing is checked — frontmatter, every link
resolves inside the zip, no string a secret scanner would flag, Agensi's 50 MB
limit — and zipped as <skill>/... with fixed timestamps, so an unchanged
listing produces a byte-identical zip.

    python3 marketplace/agensi.py                   # every skill and bundle → dist/agensi/
    python3 marketplace/agensi.py appsec incident-response
    python3 marketplace/agensi.py --out /tmp/agensi
    python3 marketplace/agensi.py --check           # build and check, write nothing

manifest.json in the output folder records each zip's hash and price; a later
run compares against it and marks each listing new, changed or unchanged,
which is the list to re-upload.

Exit status: 0 clean, 1 problems found, 2 usage error.
"""
from __future__ import annotations

import argparse
import dataclasses as dc
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
HERE = pathlib.Path(__file__).resolve().parent
PATCHES = HERE / "patches.json"
BUNDLES = HERE / "bundles.json"
ZIP_DATE = (1980, 1, 1, 0, 0, 0)
SKILL_PRICE_USD = 5
BUNDLE_PRICE_USD = 10  # flat, whatever the bundle's size
MAX_ZIP_BYTES = 50 * 1024 * 1024  # the submit form's limit
DESC_MAX = 1024
DESC_WARN = 1000  # less headroom than this and the next edit to a description fails the build

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
# One pass over the text: fences and inline code are matched so they can be
# left alone; only the link alternative is rewritten.
TOKENS = re.compile(
    r"(?P<fence>^(?P<tick>```|~~~).*?^(?P=tick))"
    r"|(?P<code>`[^`\n]*`)"
    r"|(?P<link>(?P<bang>!?)\[(?P<text>[^\]\n]*)\]\((?P<href>[^)\s]+)\))",
    re.S | re.M,
)
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SECRETS = [
    ("an OpenAI-style key", re.compile(r"\bsk-(live|test|proj)-")),
    ("an AWS access key", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("a GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b")),
    ("a GitLab token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20}\b")),
    ("a Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("a private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]


@dc.dataclass
class Package:
    """One skill folder as it will sit in a zip."""
    name: str
    members: frozenset[str] = frozenset()  # the bundle this package ships in, itself included
    files: dict[str, str] = dc.field(default_factory=dict)  # package path → text
    vendored: dict[str, str] = dc.field(default_factory=dict)  # package path → repo path
    related: set[str] = dc.field(default_factory=set)
    demoted: list[str] = dc.field(default_factory=list)  # links turned into text
    problems: list[str] = dc.field(default_factory=list)
    warnings: list[str] = dc.field(default_factory=list)
    description_length: int = 0


@dc.dataclass
class Listing:
    """What gets uploaded: one skill, or a bundle of several."""
    name: str
    packages: list[Package]
    problems: list[str] = dc.field(default_factory=list)

    @property
    def kind(self) -> str:
        return "bundle" if len(self.packages) > 1 else "skill"

    @property
    def price_usd(self) -> int:
        return BUNDLE_PRICE_USD if self.kind == "bundle" else SKILL_PRICE_USD

    def all_problems(self) -> list[str]:
        return self.problems + [p for pkg in self.packages for p in pkg.problems]


def discover(skills_dir: pathlib.Path | None = None) -> dict[str, pathlib.Path]:
    """Skill name → folder, for every SKILL.md under skills_dir (default: skills/)."""
    found = {}
    for md in sorted((skills_dir or SKILLS).rglob("SKILL.md")):
        found[md.parent.name] = md.parent
    return found


def rel(path: pathlib.Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def resolve(base: pathlib.Path, href: str) -> pathlib.Path:
    """Resolve a link lexically — a symlinked doc's links are written relative
    to where the link sits, not to the file it points at."""
    return pathlib.Path(os.path.normpath(base / href.split("#", 1)[0]))


def anchor(href: str) -> str:
    return "#" + href.split("#", 1)[1] if "#" in href else ""


def plain(text: str, skills: dict[str, pathlib.Path]) -> str:
    """Link text for a skill that isn't in this package: its name, in code style."""
    bare = text.strip("*`_ ")
    if bare in skills and "`" not in text:
        return f"`{bare}`"
    return text


def drop_section(text: str, heading: str) -> tuple[str, int]:
    """Remove the section headed by the line `heading`, up to the next heading of
    the same or a higher level, and the `---` rule that closed the section before
    it if nothing follows. Returns the text and how many such headings there were."""
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line == heading]
    if len(starts) != 1:
        return text, len(starts)
    level = len(heading) - len(heading.lstrip("#"))
    start, end, fence = starts[0], len(lines), None
    for i in range(start + 1, len(lines)):
        mark = re.match(r"(```|~~~)", lines[i])
        if mark:
            fence = None if fence == mark.group(1) else fence or mark.group(1)
        elif not fence and re.match(rf"#{{1,{level}}} ", lines[i]):
            end = i
            break
    kept = lines[:start] + lines[end:]
    if end == len(lines):  # the last section: drop the rule left dangling above it
        while kept and kept[-1].strip() in ("", "---"):
            kept.pop()
        kept.append("")
    return "\n".join(kept), 1


def apply_patches(pkg: Package, patches: dict) -> None:
    for path, edits in patches.get(pkg.name, {}).items():
        if path not in pkg.files:
            pkg.problems.append(f"patches.json: {pkg.name}/{path} is not in the package")
            continue
        text = pkg.files[path]
        for edit in edits:
            if "drop_section" in edit:
                text, count = drop_section(text, edit["drop_section"])
                if count != 1:
                    pkg.problems.append(
                        f"patches.json: {pkg.name}/{path}: section heading matches {count} times, not once — "
                        f"the source changed; update or drop it: {edit['drop_section']!r}")
                continue
            count = text.count(edit["old"])
            if count != 1:
                pkg.problems.append(
                    f"patches.json: {pkg.name}/{path}: patch matches {count} times, not once — "
                    f"the source changed; update or drop it: {edit['old'][:60]!r}")
                continue
            text = text.replace(edit["old"], edit["new"])
        pkg.files[path] = text


def rewrite(pkg: Package, path: str, source: pathlib.Path, skill_dir: pathlib.Path,
            skills: dict[str, pathlib.Path], queue: list) -> None:
    """Rewrite one package file's links. source is where the file sits in the repo
    (the symlink, not its target), which is what its relative links mean."""

    def sub(m: re.Match) -> str:
        if not m.group("link"):
            return m.group(0)
        text, href, bang = m.group("text"), m.group("href"), m.group("bang")
        if re.match(r"[a-z][a-z0-9+.-]*:|#", href):
            return m.group(0)
        target = resolve(source.parent, href)
        if not target.exists():
            # A symlinked doc whose link was written for where its target lives.
            target = resolve(source.resolve().parent, href)
        if not target.exists():
            return m.group(0)  # left for the check to report
        here = os.path.dirname(path) or "."
        folder = target.parent.resolve()  # folders aren't symlinks; this only settles /tmp vs /private/tmp
        if folder == skill_dir.resolve():
            # Its own doc — the href changes only when a copied doc points back here.
            return f"{bang}[{text}]({os.path.relpath(target.name, here)}{anchor(href)})"
        owner = target.parent.name
        if owner in pkg.members and owner in skills and folder == skills[owner].resolve():
            # A sibling in the same bundle: the link stays live.
            local = os.path.relpath(os.path.join("..", owner, target.name), here)
            return f"{bang}[{text}]({local}{anchor(href)})"
        inside_skills = folder.is_relative_to(SKILLS.resolve())
        if inside_skills and target.name == "SKILL.md" and owner in skills:
            pkg.related.add(owner)
            return plain(text, skills)
        if inside_skills and target.suffix == ".md" and target.name != "README.md":
            local = vendor(pkg, target, skill_dir, queue)
            return f"{bang}[{text}]({local}{anchor(href)})"
        if bang:
            pkg.problems.append(f"{pkg.name}/{path}: image outside the skill ({href})")
            return m.group(0)
        pkg.demoted.append(f"{path}: {href}")
        return text

    pkg.files[path] = TOKENS.sub(sub, pkg.files[path])


def vendor(pkg: Package, target: pathlib.Path, skill_dir: pathlib.Path, queue: list) -> str:
    """Copy another skill's reference doc into the package; return its package path."""
    for local in pkg.files:
        own = skill_dir / local
        if own.exists() and own.resolve() == target.resolve():
            return local  # the skill already ships this doc, as a symlink to it
    repo_path = rel(target.resolve())  # one copy, however many symlinks lead to it
    for local, origin in pkg.vendored.items():
        if origin == repo_path:
            return local
    local = target.name if target.name not in pkg.files else f"{target.parent.name}-{target.name}"
    pkg.files[local] = target.read_text()
    pkg.vendored[local] = repo_path
    queue.append((local, target))
    return local


def related_section(pkg: Package) -> str:
    names = " · ".join(f"`{n}`" for n in sorted(pkg.related))
    return (
        "\n\n## Related skills\n\n"
        f"This skill refers to these by name: {names}. Each is a separate skill, "
        "published on its own; none of them has to be installed for this one to run.\n"
    )


def check(pkg: Package, known: set[str]) -> None:
    """known is every path in the zip this package ships in, as <skill>/<file>."""
    skill_md = pkg.files.get("SKILL.md")
    if skill_md is None:
        pkg.problems.append(f"{pkg.name}: no SKILL.md")
        return
    m = FRONTMATTER.match(skill_md)
    if not m:
        pkg.problems.append(f"{pkg.name}/SKILL.md: no YAML frontmatter")
    else:
        fields = dict(re.findall(r"^(\w[\w-]*):\s*(.*)$", m.group(1), re.M))
        name = fields.get("name", "").strip()
        desc = fields.get("description", "").strip().strip('"')
        if name != pkg.name:
            pkg.problems.append(f"{pkg.name}/SKILL.md: name {name!r} does not match the folder")
        if not NAME.match(name) or len(name) > 64:
            pkg.problems.append(f"{pkg.name}/SKILL.md: name must be lowercase letters, digits and hyphens, ≤64")
        if re.search(r"anthropic|claude", name):
            pkg.problems.append(f"{pkg.name}/SKILL.md: name may not contain 'anthropic' or 'claude'")
        pkg.description_length = len(desc)
        if not desc or len(desc) > DESC_MAX:
            pkg.problems.append(f"{pkg.name}/SKILL.md: description must be 1–{DESC_MAX} characters ({len(desc)})")
        if re.search(r"<[a-zA-Z/][^>]*>", desc):
            pkg.problems.append(f"{pkg.name}/SKILL.md: description contains an XML/HTML tag")

    for path, text in sorted(pkg.files.items()):
        for m in TOKENS.finditer(text):
            if not m.group("link"):
                continue
            href = m.group("href")
            if re.match(r"[a-z][a-z0-9+.-]*:|#", href):
                continue
            target = os.path.normpath(os.path.join(pkg.name, os.path.dirname(path), href.split("#", 1)[0]))
            if target not in known:
                pkg.problems.append(f"{pkg.name}/{path}: link does not resolve inside the zip ({href})")
        for kind, pattern in SECRETS:
            for hit in pattern.finditer(text):
                line = text.count("\n", 0, hit.start()) + 1
                pkg.problems.append(f"{pkg.name}/{path}:{line}: looks like {kind} — a secret scanner will flag it")
        # "a throwaway harness" is a test harness; only this repo's harness is missing.
        mentions = len(re.findall(r"\bthe harness\b|\bharness/", text, re.I))
        if mentions:
            pkg.warnings.append(f"{path} ({mentions})")


def build(name: str, skills: dict[str, pathlib.Path], patches: dict,
          members: frozenset[str] = frozenset()) -> Package:
    skill_dir = skills[name]
    pkg = Package(name, members=members or frozenset({name}))
    for f in sorted(skill_dir.rglob("*")):
        if f.is_file():
            pkg.files[str(f.relative_to(skill_dir))] = f.read_text()
    apply_patches(pkg, patches)
    queue = [(path, skill_dir / path) for path in sorted(pkg.files)]
    while queue:
        path, source = queue.pop(0)
        rewrite(pkg, path, source, skill_dir, skills, queue)
    if pkg.related:
        pkg.files["SKILL.md"] = pkg.files["SKILL.md"].rstrip("\n") + related_section(pkg)
    return pkg


def build_listing(name: str, members: list[str], skills: dict[str, pathlib.Path], patches: dict) -> Listing:
    group = frozenset(members)
    listing = Listing(name, [build(m, skills, patches, group) for m in members])
    known = {f"{pkg.name}/{path}" for pkg in listing.packages for path in pkg.files}
    for pkg in listing.packages:
        check(pkg, known)
    size = len(zip_bytes(listing))
    if size > MAX_ZIP_BYTES:
        listing.problems.append(f"{name}: zip is {size / 2**20:.1f} MB; Agensi takes at most 50 MB")
    return listing


def load_bundles(skills: dict[str, pathlib.Path]) -> tuple[dict[str, list[str]], list[str]]:
    """bundles.json → {bundle: [skills]}, and whatever is wrong with it."""
    bundles = json.loads(BUNDLES.read_text()) if BUNDLES.exists() else {}
    problems = []
    for name, members in bundles.items():
        if not NAME.match(name):
            problems.append(f"bundles.json: {name!r} must be lowercase letters, digits and hyphens")
        if name in skills:
            problems.append(f"bundles.json: {name!r} is also a skill's name")
        if len(members) < 2 or len(set(members)) != len(members):
            problems.append(f"bundles.json: {name!r} needs two or more distinct skills")
        for m in members:
            if m not in skills:
                problems.append(f"bundles.json: {name!r} names {m!r}, which no SKILL.md defines")
    return bundles, problems


def zip_bytes(listing: Listing) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        entries = sorted((f"{pkg.name}/{path}", text)
                         for pkg in listing.packages for path, text in pkg.files.items())
        for arcname, text in entries:
            info = zipfile.ZipInfo(arcname, date_time=ZIP_DATE)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, text.encode())
    return buf.getvalue()


def git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("names", nargs="*", help="skill or bundle names (default: every skill and bundle)")
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "dist" / "agensi")
    ap.add_argument("--check", action="store_true", help="build and check only; write nothing")
    args = ap.parse_args(argv)

    skills = discover()
    bundles, problems = load_bundles(skills)
    unknown = [n for n in args.names if n not in skills and n not in bundles]
    if unknown:
        print(f"unknown skill or bundle: {', '.join(unknown)}", file=sys.stderr)
        return 2
    patches = json.loads(PATCHES.read_text())
    problems += [f"patches.json: no skill named {s!r}" for s in sorted(set(patches) - set(skills))]
    if problems:
        bundles = {}  # a broken bundles.json is reported, not built
    names = args.names or sorted(skills) + sorted(bundles)
    listings = [build_listing(n, bundles.get(n, [n]), skills, patches) for n in names
                if n in skills or n in bundles]
    problems += [p for listing in listings for p in listing.all_problems()]

    previous = {}
    manifest_path = args.out / "manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text()).get("listings", {})
    manifest = {"commit": git_head(),
                "listings": dict(previous)}

    if not args.check and not problems:
        args.out.mkdir(parents=True, exist_ok=True)
    print(f"{'listing':<24}{'skills':>7}{'files':>7}{'copied':>8}{'price':>7}  status")
    for listing in listings:
        data = zip_bytes(listing)
        digest = hashlib.sha256(data).hexdigest()
        old = previous.get(listing.name, {}).get("sha256")
        status = "new" if old is None else "unchanged" if old == digest else "changed"
        if listing.all_problems():
            status = "FAILED"
        pkgs = listing.packages
        files = sum(len(p.files) for p in pkgs)
        copied = sum(len(p.vendored) for p in pkgs)
        print(f"{listing.name:<24}{len(pkgs):>7}{files:>7}{copied:>8}{'$' + str(listing.price_usd):>7}  {status}")
        if args.check or problems:
            continue
        (args.out / f"{listing.name}.zip").write_bytes(data)
        manifest["listings"][listing.name] = {
            "kind": listing.kind,
            "price_usd": listing.price_usd,
            "sha256": digest,
            "skills": {
                pkg.name: {
                    "files": sorted(pkg.files),
                    "copied_from_other_skills": pkg.vendored,
                    "related": sorted(pkg.related),
                    "links_made_plain": pkg.demoted,
                } for pkg in pkgs
            },
        }

    seen, mentions = set(), []
    for pkg in (p for listing in listings for p in listing.packages):
        if pkg.warnings and pkg.name not in seen:
            seen.add(pkg.name)
            mentions.append(f"  {pkg.name}: {', '.join(pkg.warnings)}")
    if mentions:
        print("\nmentions the repo's harness, which a zip does not ship:")
        print("\n".join(mentions))
    long = sorted({(pkg.name, pkg.description_length) for listing in listings for pkg in listing.packages
                   if DESC_WARN < pkg.description_length <= DESC_MAX}, key=lambda x: -x[1])
    if long:
        print(f"\ndescriptions within {DESC_MAX - DESC_WARN} characters of the {DESC_MAX} limit:")
        print("\n".join(f"  {name}: {n}" for name, n in long))
    if problems:
        print("\nproblems:")
        for p in dict.fromkeys(problems):
            print(f"  {p}")
        if not args.check:
            print("\nnothing written")
        return 1
    if not args.check:
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        print(f"\n{len(listings)} zip(s) in {rel(args.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
