#!/usr/bin/env python3
"""Keep the shared reference files in step with their one source.

Some reference docs (and netgraph.py) serve several skills. Each skill folder
must carry its own copy: `npx skills add` installs a folder on its own and drops
any symlink that points outside it. skills/shared.json maps every source to the
copies made of it. Edit the source, never a copy; this script writes the copies.

Keys starting with `_` are notes, not sources. `_why` maps each source to why
the skills that read it carry a copy rather than a pointer to it (`_why._` is
the reason they share); --check fails on a source with no reason, and on a
reason for a source that isn't listed.

    python3 .github/scripts/sync_shared.py            # rewrite stale copies from their sources
    python3 .github/scripts/sync_shared.py --check    # exit 1 if any copy differs (CI, check_repo)
    python3 .github/scripts/sync_shared.py --staged   # pre-commit: sync from the index and stage

A copy that was edited directly is never overwritten: the script stops and
names the source the edit belongs in. Install the pre-commit hook once per
clone with `git config core.hooksPath .githooks`.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "skills/shared.json"


def sources(manifest):
    """{source: [copy, ...]} from a parsed manifest, without its `_` notes."""
    return {k: v for k, v in manifest.items() if not k.startswith("_")}


def pairs():
    """(source, copy) for every copy in the manifest, as repo-relative paths."""
    for source, copies in sources(json.loads(MANIFEST.read_text())).items():
        for copy in copies:
            yield source, copy


def unexplained(manifest):
    """Messages for a source with no `_why` reason, and for a reason with no source."""
    why = {k for k in manifest.get("_why", {}) if not k.startswith("_")}
    listed = set(sources(manifest))
    return ([f"skills/shared.json: {s} has no reason in _why (why can't its skills point at one file?)"
             for s in sorted(listed - why)] +
            [f"skills/shared.json: _why explains {s}, which is not a listed source"
             for s in sorted(why - listed)])


def git_bytes(rev_path):
    """A file's bytes at `HEAD:path` or `:path` (the index), or None."""
    out = subprocess.run(["git", "show", rev_path], cwd=ROOT, capture_output=True)
    return out.stdout if out.returncode == 0 else None


def work_bytes(path):
    p = ROOT / path
    return None if p.is_symlink() or not p.is_file() else p.read_bytes()


def stale():
    """Messages for every copy that is missing, a symlink, or differs from its
    source, and for every source without a `_why` reason."""
    out = unexplained(json.loads(MANIFEST.read_text()))
    for source, copy in pairs():
        p = ROOT / copy
        if p.is_symlink():
            out.append(f"{copy}: a symlink — the installer drops it; make it a copy of {source}")
        elif not p.is_file():
            out.append(f"{copy}: missing — it is a copy of {source}")
        elif p.read_bytes() != (ROOT / source).read_bytes():
            out.append(f"{copy}: differs from {source} — edit the source, then run "
                       f"python3 .github/scripts/sync_shared.py")
        elif (p.stat().st_mode & 0o111) != ((ROOT / source).stat().st_mode & 0o111):
            out.append(f"{copy}: executable bit differs from {source}")
    return out


def sync(staged):
    """Rewrite each stale copy from its source. With staged, the source is read
    from the index and the copy is staged. Returns error messages."""
    errors, written = [], []
    for source, copy in pairs():
        src = git_bytes(f":{source}") if staged else work_bytes(source)
        if src is None:
            errors.append(f"{source}: listed in skills/shared.json but not found")
            continue
        p = ROOT / copy
        current = git_bytes(f":{copy}") if staged else work_bytes(copy)
        if current == src and not p.is_symlink():
            continue
        # The copy changed only because its source did — unless someone edited it.
        before = git_bytes(f"HEAD:{copy}")
        edited = current is not None and current != before and not p.is_symlink()
        if staged and work_bytes(copy) not in (current, None):
            edited = True  # unstaged edits in the copy would be lost
        if edited:
            errors.append(f"{copy} was edited directly. Move the change into {source}, "
                          f"then run python3 .github/scripts/sync_shared.py")
            continue
        if p.is_symlink():
            p.unlink()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(src)
        p.chmod((ROOT / source).stat().st_mode & 0o777)
        written.append(copy)
    if staged and written:
        subprocess.run(["git", "add", "--", *written], cwd=ROOT, check=True)
    for copy in written:
        print(f"synced {copy}")
    return errors


def main():
    if "--check" in sys.argv:
        problems = stale()
    else:
        problems = sync(staged="--staged" in sys.argv)
    for msg in problems:
        print(msg, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
