"""Check the plugin manifests against the skills that exist and the released
version: the Claude Code marketplace, the Codex marketplace and manifest, and
the slash commands the Claude Code plugin ships.

check_repo.py calls check(); it lives here so evals/tests/test_plugins.py can
test it on a small fake tree without running every other repo check.

Formats, as of 2026-11-24:
  Claude Code  https://code.claude.com/docs/en/plugins-reference (a marketplace
               entry with no plugin.json is the plugin's manifest; `commands`
               lists .md files relative to the plugin root)
  Codex        https://developers.openai.com/codex/plugins/build (the repo
               marketplace at .agents/plugins/marketplace.json; the compatibility
               manifest .codex-plugin/plugin.json at the plugin root, whose
               `skills` takes `./`-prefixed paths, per openai/codex
               codex-rs/core-plugins/src/manifest.rs)
"""
import json
import re

import registry

CLAUDE = ".claude-plugin/marketplace.json"
CODEX_MARKET = ".agents/plugins/marketplace.json"
CODEX_PLUGIN = "skills/.codex-plugin/plugin.json"
COMMANDS = "skills/commands"
# Metadata the Codex manifest repeats from the Claude Code entry, so the two
# installs describe the same plugin.
SAME = ("name", "version", "description", "author", "homepage", "repository", "license")

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
SKILL_NAME = re.compile(r"`([a-z][a-z0-9-]*)`")


def load(root, rel, out):
    try:
        return json.loads((root / rel).read_text())
    except FileNotFoundError:
        out.append(f"{rel}: missing")
    except ValueError as e:
        out.append(f"{rel}: does not parse ({e})")
    return None


def check(root, skills):
    """Problems with the plugin manifests and commands under root, given
    {skill name: repo-relative path of its SKILL.md}."""
    out = []
    families = sorted({f"./{rel.parts[1]}" for rel in skills.values()})
    released = registry.version(root)

    # ---- Claude Code
    market = load(root, CLAUDE, out)
    entries = market.get("plugins", []) if isinstance(market, dict) else []
    entry = None
    if market is not None:
        if len(entries) != 1 or entries[0].get("source") != "./skills" or entries[0].get("strict") is not False:
            out.append(f"{CLAUDE}: needs exactly one plugin with \"source\": \"./skills\" and \"strict\": false "
                       f"(a root source installs harness/ and evals/ too)")
        else:
            entry = entries[0]
    if entry is not None:
        if sorted(entry.get("skills", [])) != families:
            out.append(f"{CLAUDE}: skills is {sorted(entry.get('skills', []))}, expected the family folders {families}")
        if entry.get("version") != released:
            out.append(f"{CLAUDE}: version {entry.get('version')!r} is not the top released version in "
                       f"CHANGELOG.md ({released!r}); a release moves both")
        out += commands(root, entry.get("commands", []), skills)
    if (root / ".claude-plugin/plugin.json").exists():
        out.append(".claude-plugin/plugin.json: the marketplace entry is the plugin's whole definition "
                   "(strict false); a plugin.json beside it would be a second, unchecked one")

    # ---- Codex
    codex_market = load(root, CODEX_MARKET, out)
    if codex_market is not None:
        plugins = codex_market.get("plugins", []) if isinstance(codex_market, dict) else []
        source = plugins[0].get("source") if len(plugins) == 1 else None
        path = source.get("path") if isinstance(source, dict) else source
        if path != "./skills":
            out.append(f"{CODEX_MARKET}: needs exactly one plugin whose source path is \"./skills\" "
                       f"(a root source installs harness/ and evals/ too)")
        elif entry is not None and plugins[0].get("name") != entry.get("name"):
            out.append(f"{CODEX_MARKET}: plugin name {plugins[0].get('name')!r} is not {entry.get('name')!r}, "
                       f"the name in {CLAUDE}")
    manifest = load(root, CODEX_PLUGIN, out)
    if isinstance(manifest, dict):
        if manifest.get("version") != released:
            out.append(f"{CODEX_PLUGIN}: version {manifest.get('version')!r} is not the top released version "
                       f"in CHANGELOG.md ({released!r}); a release moves it with {CLAUDE}")
        if sorted(manifest.get("skills") or []) != families:
            out.append(f"{CODEX_PLUGIN}: skills is {sorted(manifest.get('skills') or [])}, expected the family "
                       f"folders {families} (relative to skills/, the plugin root)")
        if entry is not None:
            for key in SAME:
                if key != "version" and manifest.get(key) != entry.get(key):
                    out.append(f"{CODEX_PLUGIN}: {key} differs from the {CLAUDE} entry; keep the two the same")
    return out


def commands(root, declared, skills):
    """Problems with the slash commands: each declared path is a file under
    skills/commands/, every file there is declared, each has a description and
    runs only when typed, and every backticked lowercase name in it is a skill
    that exists."""
    out = []
    folder = root / COMMANDS
    present = sorted(f"./commands/{p.name}" for p in folder.glob("*.md")) if folder.is_dir() else []
    for path in declared:
        if not re.fullmatch(r"\./commands/[a-z0-9-]+\.md", path):
            out.append(f"{CLAUDE}: command {path!r} is not ./commands/<name>.md")
        elif path not in present:
            out.append(f"{CLAUDE}: command {path} does not exist under skills/")
    for path in present:
        if path not in declared:
            out.append(f"{COMMANDS}/{path.rsplit('/', 1)[1]}: not listed in {CLAUDE} commands, so Claude Code "
                       f"doesn't load it")
            continue
        rel = f"skills/{path[2:]}"
        text = (root / rel).read_text()
        m = FRONTMATTER.match(text)
        if not m or not re.search(r"^description:\s*\S", m.group(1), re.M):
            out.append(f"{rel}: needs frontmatter with a description (Codex skips a command without one)")
        elif not re.search(r"^disable-model-invocation:\s*true\s*$", m.group(1), re.M):
            out.append(f"{rel}: needs `disable-model-invocation: true`; Claude Code loads a command as a "
                       f"skill, and one Claude may pick on its own competes with the skill it routes to")
        named = SKILL_NAME.findall(text[m.end():] if m else text)
        if not named:
            out.append(f"{rel}: names no skill; a command routes to skills in backticks")
        for name in sorted(set(named) - set(skills)):
            out.append(f"{rel}: names `{name}`, which no SKILL.md defines")
    return out
