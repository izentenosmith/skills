#!/usr/bin/env python3
"""repo-memory — lint a repository's .memory/ tree, and list what a dream pass should read.

    python3 -I memlint.py audit --root . [--today YYYY-MM-DD] [--json audit.json]
    python3 -I memlint.py delta --root . [--today YYYY-MM-DD] [--json delta.json]

audit  checks the tree against layout.md: the index budget, frontmatter, links, code and commit
       references that no longer resolve, secret-like strings, orphans, stale and oversized notes,
       likely duplicates, and whether a dream is due. Codes ML01-ML12, below.
delta  the dream's input: the watermark in .memory/.dream-state, the commits since it, the notes and
       pages whose referenced files those commits touched, the memory files captured since, the
       design records (ADRs, glossary) added or changed since, and the notes past their verified
       window. With no watermark, every note is listed for verification.

Every command prints markdown; `--json PATH` also writes the full result. Stdlib only, Python 3.10+,
read-only: it reads files and runs `git rev-parse`, `git rev-list`, `git log` and `git cat-file`, and
never writes to the repo. A secret-like string is reported by its kind and location, never its value.

Exit: 0 no errors · 1 audit found errors · 2 usage (no such root, bad date).
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

INDEX_MAX_LINES = 200        # Claude Code loads the first 200 lines of its memory index (CAM)
INDEX_MAX_BYTES = 25 * 1024  # ... or 25 KB, whichever comes first
NOTE_MAX_LINES = 40          # a note body past this is a page, or two notes
PAGE_MAX_LINES = 300         # a page past this has stopped abstracting (RM10)
STALE_DAYS = {"high": 30, "low": 180}
DUP_JACCARD = 0.6
DREAM_DUE_COMMITS = 25
DREAM_DUE_DAYS = 14

NOTE_TYPES = {"fact", "decision", "gotcha", "convention", "reference"}
NOTE_FIELDS = ("name", "description", "type", "source", "verified", "volatility")
PAGE_FIELDS = ("name", "description", "type", "verified", "volatility")

SEVERITY = {
    "ML01": "error",    # INDEX.md missing
    "ML02": "error",    # INDEX.md over budget
    "ML03": "error",    # frontmatter missing, incomplete or invalid
    "ML04": "error",    # broken link
    "ML05": "error",    # code or commit reference that no longer resolves
    "ML06": "error",    # secret-like string
    "ML07": "warning",  # orphan: not reachable from INDEX.md
    "ML08": "warning",  # stale: verified longer ago than its volatility allows
    "ML09": "warning",  # likely duplicate
    "ML10": "warning",  # oversized note or page
    "ML11": "error",    # symlink or path that escapes .memory/
    "ML12": "info",     # dream due, or no dream recorded
}

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
WIKILINK = re.compile(r"\[\[([^\]|#\n]+)(?:[|#][^\]\n]*)?\]\]")
MDLINK = re.compile(r"\]\(([^)\s]+)\)")
FENCE = re.compile(r"^(```|~~~).*?^\1", re.S | re.M)
CODESPAN = re.compile(r"`([^`\n]+)`")
# a path with a directory or a known extension, optionally `:line` or `::symbol`
PATHREF = re.compile(r"^(?P<path>(?:\.{0,2}/)?[\w.@+-]+(?:/[\w.@+-]+)*)(?::(?P<line>\d+)|::(?P<sym>[A-Za-z_][\w.]*))?$")
EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".kt", ".go", ".rs", ".rb", ".php",
        ".cs", ".c", ".h", ".cc", ".cpp", ".swift", ".scala", ".sh", ".sql", ".tf", ".yml", ".yaml", ".toml",
        ".json", ".ini", ".cfg", ".md", ".txt", ".html", ".css", ".vue", ".svelte", ".proto", ".env"}
# where a repo keeps its design records: the dream links these from memory, never copies them
RECORDS = re.compile(r"^(?:(?:docs?/)?(?:adr|adrs|decisions)/.+\.md|(?:docs/)?(?:GLOSSARY|CONTEXT|glossary)\.md)$")
SHA = re.compile(r"(?<![\w-])[0-9a-f]{7,40}(?![\w-])")
STOP = set("the and for with that this from are was were has have not but its into when then than any all "
           "each per via use used uses using our their they them there here what which who will would should "
           "can could must may also only always never does did done".split())
SECRETS = [
    ("a private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("an AWS access key", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("a GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b")),
    ("a GitLab token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20}\b")),
    ("a Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("an OpenAI-style key", re.compile(r"\bsk-(live|test|proj|ant)-[A-Za-z0-9_-]{8,}")),
    ("credentials in a URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s/]{3,}@")),
    ("an assigned password, secret, key or token", re.compile(
        r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?key|token)\b\s*[:=]\s*['\"]?"
        r"(?=[^\s'\"]*\d)(?=[^\s'\"]*[A-Za-z])[^\s'\"]{8,}")),
]


class Usage(Exception):
    pass


# ------------------------------------------------------------------ helpers

def git(root, *args):
    r = subprocess.run(["git", "-C", str(root), "-c", "core.quotepath=off", *args],
                       capture_output=True, text=True, errors="replace")
    return r.returncode, r.stdout


def is_git(root):
    return git(root, "rev-parse", "--is-inside-work-tree")[0] == 0


def parse_date(s):
    try:
        return datetime.date.fromisoformat(str(s).strip()[:10])
    except ValueError:
        return None


def frontmatter(text):
    m = FRONTMATTER.match(text)
    if not m:
        return None, text
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "#")):
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip().strip("\"'")
    return fields, text[m.end():]


def prose(text):
    """The text with fenced blocks removed: links and references inside a fence are examples."""
    return FENCE.sub("", text)


def words(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) >= 3 and w not in STOP}


class Memory:
    """The parsed .memory/ tree: INDEX.md, notes/, wiki/, log/, .dream-state."""

    def __init__(self, root, mem=".memory"):
        self.root = pathlib.Path(root).resolve()
        if not self.root.is_dir():
            raise Usage(f"no such root: {root}")
        self.dir = self.root / mem
        self.git = is_git(self.root)
        self.head = git(self.root, "rev-parse", "HEAD")[1].strip() if self.git else ""
        self.files = {}          # rel (to .memory) -> text
        self.meta = {}           # rel -> frontmatter dict or None
        self.body = {}           # rel -> body text
        self.links = []          # (src rel, target text, resolved rel or None, line)
        self.escapes = []        # rel of symlinks or files resolving outside .memory/
        if self.dir.is_dir():
            self._load()
        self.state = self._state()

    def rel(self, p):
        return p.relative_to(self.dir).as_posix()

    def _load(self):
        base = self.dir.resolve()
        for p in sorted(self.dir.rglob("*.md")):
            rel = self.rel(p)
            try:
                p.resolve().relative_to(base)
            except ValueError:
                self.escapes.append(rel)
                continue
            if p.is_symlink():
                self.escapes.append(rel)
            text = p.read_text(errors="replace")
            self.files[rel] = text
            self.meta[rel], self.body[rel] = frontmatter(text)
        for rel, text in self.files.items():
            body = prose(text)
            for m in WIKILINK.finditer(body):
                slug = m.group(1).strip()
                hit = next((c for c in (f"notes/{slug}.md", f"wiki/{slug}.md") if c in self.files), None)
                self.links.append((rel, f"[[{slug}]]", hit, body.count("\n", 0, m.start()) + 1))
            for m in MDLINK.finditer(CODESPAN.sub("", body)):
                target = m.group(1)
                if re.match(r"[a-z][a-z0-9+.-]*:|#", target):
                    continue
                path = target.split("#", 1)[0]
                if not path:
                    continue
                dest = (self.dir / rel).parent / path
                try:
                    hit = dest.resolve().relative_to(base).as_posix()
                except ValueError:  # a link out of .memory/ into the repo
                    hit = "<repo>" if dest.exists() else None
                else:
                    hit = hit if dest.exists() else None
                self.links.append((rel, target, hit, body.count("\n", 0, m.start()) + 1))

    def _state(self):
        p = self.dir / ".dream-state"
        if not p.is_file():
            return {}
        out = {}
        for line in p.read_text(errors="replace").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip()
        return out

    @property
    def notes(self):
        return [r for r in self.files if r.startswith("notes/")]

    @property
    def pages(self):
        return [r for r in self.files if r.startswith("wiki/")]

    def refs(self, rel):
        """(kind, token, path, line_no) for every code and commit reference in a note or page."""
        out = []
        meta, body = self.meta.get(rel) or {}, prose(self.body.get(rel, ""))
        for m in CODESPAN.finditer(body):
            ref = pathref(m.group(1))
            if ref:
                out.append(("path", m.group(1), ref, body.count("\n", 0, m.start()) + 1))
        for tok in re.split(r"[\s,;()]+", meta.get("source", "")):
            tok = tok.strip("`'\".")
            ref = pathref(tok)
            if ref and "/" in tok:
                out.append(("path", tok, ref, 0))
            elif SHA.fullmatch(tok) and not tok.isdigit():
                out.append(("commit", tok, None, 0))
        return out


def pathref(token):
    """(path, line, symbol) if the token reads as a repo path, else None."""
    if "://" in token or token.startswith(("-", "$", "~")) or " " in token:
        return None
    m = PATHREF.match(token)
    if not m:
        return None
    path = m.group("path")
    if "/" not in path and pathlib.PurePosixPath(path).suffix not in EXTS:
        return None
    if path.startswith(("/memories", "/")):
        return None
    return path.removeprefix("./"), m.group("line"), m.group("sym")


def resolve_ref(mem, path, line, sym):
    """None if it resolves, else why not."""
    p = mem.root / path
    if not p.exists() and "/" not in path:
        # a bare file name names the file wherever it is, when exactly one file has that name
        hits = [h for h in mem.root.rglob(path) if h.is_file() and ".git" not in h.relative_to(mem.root).parts]
        if len(hits) == 1:
            p = hits[0]
    if not p.exists():
        if path.startswith(".memory/") or (mem.dir / path).exists():
            return None
        if pathlib.PurePosixPath(path).suffix not in EXTS and not (mem.root / path.split("/")[0]).exists():
            return None  # reads like a path, but not into this repo: a vault key, a bucket, a URL path
        return "no such file"
    if p.is_dir() or not (line or sym):
        return None
    text = p.read_text(errors="replace")
    if line and int(line) > text.count("\n") + 1:
        return f"the file has {text.count(chr(10)) + 1} lines"
    if sym and not re.search(rf"\b{re.escape(sym.split('.')[-1])}\b", text):
        return f"`{sym.split('.')[-1]}` does not appear in it"
    return None


# ------------------------------------------------------------------ audit

def audit(mem, today):
    findings = []

    def add(code, where, what):
        findings.append({"code": code, "severity": SEVERITY[code], "where": where, "what": what})

    if not mem.dir.is_dir():
        add("ML01", ".memory/", "no .memory/ directory: install has not run")
        return findings, {}
    index = mem.files.get("INDEX.md")
    if index is None:
        add("ML01", ".memory/INDEX.md", "missing: nothing is injected, so no session finds the memory")
    else:
        lines, size = index.count("\n") + (0 if index.endswith("\n") else 1), len(index.encode())
        if lines > INDEX_MAX_LINES or size > INDEX_MAX_BYTES:
            add("ML02", ".memory/INDEX.md",
                f"{lines} lines, {size / 1024:.1f} KB: over the {INDEX_MAX_LINES}-line / 25 KB budget, "
                f"so what is past it is never loaded")

    for rel in mem.escapes:
        add("ML11", f".memory/{rel}", "a symlink or a path that resolves outside .memory/")

    for rel in mem.notes + mem.pages:
        meta = mem.meta[rel]
        is_note = rel.startswith("notes/")
        where = f".memory/{rel}"
        if meta is None:
            add("ML03", where, "no frontmatter")
            continue
        need = NOTE_FIELDS if is_note else PAGE_FIELDS
        missing = [f for f in need if not meta.get(f)]
        if missing:
            add("ML03", where, f"missing {', '.join(missing)}")
        stem = pathlib.PurePosixPath(rel).stem
        if meta.get("name") and meta["name"] != stem:
            add("ML03", where, f"name {meta['name']!r} does not match the file name {stem!r}")
        t = meta.get("type", "")
        if t and is_note and t not in NOTE_TYPES:
            add("ML03", where, f"type {t!r} is not one of {', '.join(sorted(NOTE_TYPES))}")
        if t and not is_note and t != "entity":
            add("ML03", where, f"a wiki page has type {t!r}; pages are type: entity")
        vol = meta.get("volatility", "")
        if vol and vol not in STALE_DAYS:
            add("ML03", where, f"volatility {vol!r} is not low or high")
        verified = parse_date(meta.get("verified", "")) if meta.get("verified") else None
        if meta.get("verified") and verified is None:
            add("ML03", where, f"verified {meta['verified']!r} is not a YYYY-MM-DD date")
        if verified and vol in STALE_DAYS and (today - verified).days > STALE_DAYS[vol]:
            add("ML08", where, f"verified {verified}, {(today - verified).days} days ago "
                               f"(volatility {vol}: re-check after {STALE_DAYS[vol]})")
        n = mem.body[rel].strip().count("\n") + 1
        if is_note and n > NOTE_MAX_LINES:
            add("ML10", where, f"{n} lines: a note holds one fact; this is a page, or several notes")
        if not is_note and n > PAGE_MAX_LINES:
            add("ML10", where, f"{n} lines: a page this long has stopped abstracting")
        for kind, tok, ref, line in mem.refs(rel):
            at = f"{where}:{line}" if line else f"{where} (source)"
            if kind == "path":
                why = resolve_ref(mem, *ref)
                if why:
                    add("ML05", at, f"`{tok}`: {why}")
            elif mem.git and git(mem.root, "cat-file", "-e", f"{tok}^{{commit}}")[0]:
                add("ML05", at, f"commit {tok} is not in this repository")

    for src, target, hit, line in mem.links:
        if hit is None:
            add("ML04", f".memory/{src}:{line}", f"{target} points at nothing")

    for rel, text in mem.files.items():
        for i, line in enumerate(text.splitlines(), 1):
            for kind, rx in SECRETS:
                if rx.search(line):
                    add("ML06", f".memory/{rel}:{i}", f"{kind} (value not shown): remove it and rotate it")
                    break

    if index is not None:
        seen, todo = {"INDEX.md"}, ["INDEX.md"]
        edges = {}
        for src, _, hit, _ in mem.links:
            if hit and hit != "<repo>":
                edges.setdefault(src, set()).add(hit)
        while todo:
            for nxt in edges.get(todo.pop(), ()):
                if nxt not in seen:
                    seen.add(nxt)
                    todo.append(nxt)
        for rel in mem.notes + mem.pages:
            if rel not in seen:
                add("ML07", f".memory/{rel}", "not reachable from INDEX.md, so no session will find it")

    docs = [(rel, words((mem.meta[rel] or {}).get("description", "")), mem.body[rel].strip())
            for rel in mem.notes + mem.pages if mem.meta[rel]]
    for i, (a, wa, ba) in enumerate(docs):
        for b, wb, bb in docs[i + 1:]:
            j = len(wa & wb) / len(wa | wb) if wa and wb else 0
            if j >= DUP_JACCARD or (ba and ba == bb):
                add("ML09", f".memory/{a}", f"likely the same memory as .memory/{b} "
                                            f"({'identical body' if ba == bb else f'descriptions {j:.0%} alike'})")

    info = dream_info(mem, today)
    if info["due"]:
        add("ML12", ".memory/.dream-state", info["due"])
    return findings, info


def dream_info(mem, today):
    w, dreamed = mem.state.get("watermark", ""), parse_date(mem.state.get("dreamed", ""))
    info = {"watermark": w, "dreamed": str(dreamed or ""), "head": mem.head, "since": None, "due": ""}
    if not mem.git:
        info["due"] = "not a git repository: no history to dream over"
        return info
    if not w:
        info["due"] = "no dream recorded: the first dream verifies every note"
        return info
    code, out = git(mem.root, "rev-list", "--count", f"{w}..HEAD")
    if code:
        info["due"] = f"watermark {w} is not an ancestor of HEAD (rewritten history?): dream as a first pass"
        return info
    info["since"] = int(out.strip())
    days = (today - dreamed).days if dreamed else None
    if info["since"] >= DREAM_DUE_COMMITS or (days is not None and days >= DREAM_DUE_DAYS and info["since"]):
        info["due"] = (f"{info['since']} commits since the last dream"
                       + (f" ({days} days ago)" if days is not None else "") + ": a dream is due")
    return info


# ------------------------------------------------------------------ delta

def delta(mem, today):
    info = dream_info(mem, today)
    w = info["watermark"] if info["since"] is not None else ""
    commits, touched = [], {}
    if mem.git:
        rng = [f"{w}..HEAD"] if w else ["HEAD"]
        code, out = git(mem.root, "log", "--no-merges", "--date=short", "--name-status",
                        "--format=%x1e%H%x09%ad%x09%s", *rng)
        if code == 0:
            for block in out.split("\x1e")[1:]:
                head, *rest = block.strip("\n").split("\n")
                sha, date, subject = (head.split("\t", 2) + ["", ""])[:3]
                paths = []
                for line in rest:
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        status = parts[0][:1]
                        paths.append({"status": status, "path": parts[-1],
                                      **({"from": parts[1]} if status in "RC" and len(parts) == 3 else {})})
                        for p in parts[1:]:
                            touched.setdefault(p, []).append(sha[:8])
                commits.append({"sha": sha, "date": date, "subject": subject, "files": paths})

    reverify = []
    for rel in mem.notes + mem.pages:
        hits = []
        for kind, tok, ref, _ in mem.refs(rel):
            if kind != "path":
                continue
            p = ref[0]
            for path, shas in touched.items():
                hit = {"ref": tok, "path": path, "commits": sorted(set(shas))}
                if (path == p or path.startswith(p.rstrip("/") + "/")) and hit not in hits:
                    hits.append(hit)
        if not w:
            reverify.append({"file": f".memory/{rel}", "why": "first dream: verify every note"})
        elif hits:
            reverify.append({"file": f".memory/{rel}", "why": hits})

    captured = sorted({p for c in commits for f in c["files"] for p in [f["path"]]
                       if p.startswith(".memory/") and not p.endswith(".dream-state")}) if w else []
    records = {}
    if w:
        for c in reversed(commits):  # oldest first, so the latest status wins
            for f in c["files"]:
                if RECORDS.match(f["path"]):
                    records[f["path"]] = {"path": f["path"], "status": f["status"], "commit": c["sha"][:8]}
    stale = [f for f in audit(mem, today)[0] if f["code"] == "ML08"]
    return {**info, "commits": commits, "reverify": reverify, "captured": captured,
            "records": sorted(records.values(), key=lambda r: r["path"]),
            "stale": [s["where"] for s in stale]}


# ------------------------------------------------------------------ output

def md_audit(mem, findings, info):
    n_err = sum(f["severity"] == "error" for f in findings)
    n_warn = sum(f["severity"] == "warning" for f in findings)
    index = mem.files.get("INDEX.md", "")
    head = f" @ {mem.head[:8]}" if mem.head else ""
    out = [f"# memlint audit — .memory{head}", ""]
    dream = (f"last dream {info.get('dreamed') or '?'} (watermark {info['watermark'][:8]}, "
             f"{info['since']} commits since)" if info.get("since") is not None else "no usable dream watermark")
    out.append(f"**Data:** {len(mem.notes)} notes, {len(mem.pages)} wiki pages, INDEX.md "
               f"{index.count(chr(10))} lines / {len(index.encode()) / 1024:.1f} KB, {dream}.")
    out.append("")
    if findings:
        out += ["| Code | Severity | Where | What |", "|---|---|---|---|"]
        order = {"error": 0, "warning": 1, "info": 2}
        for f in sorted(findings, key=lambda f: (order[f["severity"]], f["code"], f["where"])):
            out.append(f"| {f['code']} | {f['severity']} | `{f['where']}` | {f['what'].replace('|', '/')} |")
        out.append("")
    out.append(f"**Result:** {n_err} errors, {n_warn} warnings, "
               f"{sum(f['severity'] == 'info' for f in findings)} info.")
    return "\n".join(out) + "\n"


def md_delta(d):
    out = ["# memlint delta — what the dream reads", ""]
    if d["since"] is None:
        out.append(f"**Watermark:** none usable ({d['due']}). Every note is listed for verification; "
                   f"history below is the full log.")
    else:
        out.append(f"**Watermark:** {d['watermark'][:8]} (dreamed {d['dreamed'] or '?'}) → HEAD "
                   f"{d['head'][:8]}: {d['since']} commits.")
    out += ["", f"## Commits ({len(d['commits'])})", ""]
    for c in d["commits"][:200]:
        files = ", ".join(f"{f['status']} {f.get('from', '') + ' → ' if f.get('from') else ''}{f['path']}"
                          for f in c["files"][:8])
        more = f", +{len(c['files']) - 8} more" if len(c["files"]) > 8 else ""
        out.append(f"- `{c['sha'][:8]}` {c['date']} {c['subject']} — {files}{more}")
    if len(d["commits"]) > 200:
        out.append(f"- … {len(d['commits']) - 200} older commits not shown (see --json)")
    out += ["", f"## Re-verify ({len(d['reverify'])})", ""]
    for r in d["reverify"]:
        if isinstance(r["why"], str):
            out.append(f"- `{r['file']}`: {r['why']}")
        else:
            why = "; ".join(f"`{h['ref']}` → {h['path']} in {', '.join(h['commits'])}" for h in r["why"])
            out.append(f"- `{r['file']}`: {why}")
    out += ["", f"## Design records since the last dream ({len(d['records'])})", ""]
    out += [f"- {r['status']} `{r['path']}` in `{r['commit']}`" for r in d["records"]] or ["- none"]
    out += ["", f"## Captured since the last dream ({len(d['captured'])})", ""]
    out += [f"- `{p}`" for p in d["captured"]] or ["- none"]
    out += ["", f"## Past their verified window ({len(d['stale'])})", ""]
    out += [f"- `{p}`" for p in d["stale"]] or ["- none"]
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("command", choices=["audit", "delta"])
    ap.add_argument("--root", default=".", help="the repository root (default .)")
    ap.add_argument("--memory", default=".memory", help="the memory directory, relative to --root (default .memory)")
    ap.add_argument("--today", help="YYYY-MM-DD, for staleness (default: today)")
    ap.add_argument("--json", type=pathlib.Path, help="also write the full result here")
    a = ap.parse_args(argv)
    try:
        today = parse_date(a.today) if a.today else datetime.date.today()
        if today is None:
            raise Usage(f"--today {a.today!r} is not YYYY-MM-DD")
        mem = Memory(a.root, a.memory)
    except Usage as e:
        print(f"memlint: {e}", file=sys.stderr)
        return 2
    if a.command == "audit":
        findings, info = audit(mem, today)
        sys.stdout.write(md_audit(mem, findings, info))
        result = {"findings": findings, "dream": info}
        code = 1 if any(f["severity"] == "error" for f in findings) else 0
    else:
        result = delta(mem, today)
        sys.stdout.write(md_delta(result))
        code = 0
    if a.json:
        a.json.write_text(json.dumps(result, indent=2) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
