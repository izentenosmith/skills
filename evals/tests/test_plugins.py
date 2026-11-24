"""The plugin manifests (Claude Code and Codex) and the slash commands, checked
on a small fake tree; and the `_why` reasons in skills/shared.json.
Run: python3 -m unittest discover evals/tests"""
import json
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / ".github/scripts"))

import plugins  # noqa: E402
import sync_shared  # noqa: E402

META = {"name": "kit", "description": "d", "author": {"name": "a"}, "homepage": "https://h",
        "repository": "https://r", "license": "MIT"}
SKILLS = {"fixer": pathlib.PurePosixPath("skills/ops/fixer/SKILL.md"),
          "mapper": pathlib.PurePosixPath("skills/net/mapper/SKILL.md")}
COMMAND = ("---\ndescription: Fix it.\nargument-hint: \"[bug]\"\ndisable-model-invocation: true\n---\n\n"
           "Use `fixer` on $ARGUMENTS, then `mapper`.\n")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if isinstance(text, str) else json.dumps(text))


class Plugins(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        write(self.root / "CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n\n## [1.2.0] - 2026-11-21\n")
        self.claude = {"name": "m", "plugins": [{**META, "source": "./skills", "strict": False,
                                                 "version": "1.2.0", "skills": ["./net", "./ops"],
                                                 "commands": ["./commands/fix.md"]}]}
        self.market = {"name": "m", "plugins": [{"name": "kit", "source": {"source": "local", "path": "./skills"},
                                                 "policy": {"installation": "AVAILABLE"}, "category": "Coding"}]}
        self.codex = {**META, "version": "1.2.0", "skills": ["./ops", "./net"]}
        write(self.root / "skills/commands/fix.md", COMMAND)
        self.save()

    def save(self):
        write(self.root / plugins.CLAUDE, self.claude)
        write(self.root / plugins.CODEX_MARKET, self.market)
        write(self.root / plugins.CODEX_PLUGIN, self.codex)

    def problems(self):
        self.save()
        return plugins.check(self.root, SKILLS)

    def test_a_consistent_tree_passes(self):
        self.assertEqual(self.problems(), [])

    def test_codex_version_must_be_the_released_one(self):
        self.codex["version"] = "1.1.0"
        self.assertIn("is not the top released version", " ".join(self.problems()))

    def test_codex_skills_must_be_the_family_folders(self):
        self.codex["skills"] = ["./ops"]
        self.assertIn("expected the family folders", " ".join(self.problems()))

    def test_codex_metadata_must_match_the_claude_entry(self):
        self.codex["license"] = "Apache-2.0"
        self.assertEqual(self.problems(), [f"{plugins.CODEX_PLUGIN}: license differs from the "
                                           f"{plugins.CLAUDE} entry; keep the two the same"])

    def test_codex_marketplace_must_source_skills_only(self):
        self.market["plugins"][0]["source"] = "./"
        self.assertIn("source path is \"./skills\"", " ".join(self.problems()))
        self.market["plugins"][0]["source"] = "./skills"  # the plain-string form is allowed too
        self.assertEqual(self.problems(), [])

    def test_a_missing_codex_manifest_is_reported(self):
        self.save()
        (self.root / plugins.CODEX_PLUGIN).unlink()
        self.assertEqual(plugins.check(self.root, SKILLS), [f"{plugins.CODEX_PLUGIN}: missing"])

    def test_a_declared_command_must_exist(self):
        self.claude["plugins"][0]["commands"].append("./commands/gone.md")
        self.assertIn("./commands/gone.md does not exist", " ".join(self.problems()))

    def test_an_undeclared_command_file_is_reported(self):
        write(self.root / "skills/commands/extra.md", COMMAND)
        self.assertIn("extra.md: not listed", " ".join(self.problems()))

    def test_a_command_must_name_existing_skills(self):
        write(self.root / "skills/commands/fix.md", COMMAND.replace("`mapper`", "`ghost`"))
        self.assertIn("names `ghost`, which no SKILL.md defines", " ".join(self.problems()))

    def test_a_command_needs_a_description(self):
        write(self.root / "skills/commands/fix.md", "Use `fixer`.\n")
        self.assertIn("needs frontmatter with a description", " ".join(self.problems()))

    def test_a_command_runs_only_when_typed(self):
        write(self.root / "skills/commands/fix.md", COMMAND.replace("disable-model-invocation: true\n", ""))
        self.assertIn("needs `disable-model-invocation: true`", " ".join(self.problems()))

    def test_the_real_repo_passes(self):
        skills = {p.parent.name: p.relative_to(REPO) for p in (REPO / "skills").glob("*/*/SKILL.md")}
        self.assertEqual(plugins.check(REPO, skills), [])


class SharedWhy(unittest.TestCase):
    def test_every_source_needs_a_reason_and_every_reason_a_source(self):
        manifest = {"_why": {"_": "general", "a.md": "why a", "gone.md": "stale"},
                    "a.md": ["x/a.md"], "b.md": ["x/b.md"]}
        self.assertEqual(sync_shared.sources(manifest), {"a.md": ["x/a.md"], "b.md": ["x/b.md"]})
        msgs = sync_shared.unexplained(manifest)
        self.assertEqual(len(msgs), 2)
        self.assertIn("b.md has no reason", msgs[0])
        self.assertIn("_why explains gone.md", msgs[1])

    def test_the_real_manifest_explains_every_source(self):
        self.assertEqual(sync_shared.unexplained(json.loads(sync_shared.MANIFEST.read_text())), [])


if __name__ == "__main__":
    unittest.main()
