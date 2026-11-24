"""The skill registry: generated from a small fake tree (frontmatter, shared.json,
scores.json, CHANGELOG.md, CODEOWNERS), and --check failing when it is stale.
Run: python3 -m unittest discover evals/tests"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / ".github/scripts/registry.py"
sys.path.insert(0, str(SCRIPT.parent))

import registry  # noqa: E402


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class Registry(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = self.root = pathlib.Path(tmp.name)
        write(root / "skills/ops/fixer/SKILL.md",
              '---\nname: fixer\ndescription: "Fix a bug, e.g. a crash. Use when: anything breaks."\n---\nbody\n')
        write(root / "skills/ops/fixer/scripts/probe.py", "print('probe')\n")
        write(root / "skills/ops/fixer/notes.md", "not a script\n")
        write(root / "skills/ops/fixer/shared.md", "shared\n")
        write(root / "skills/net/mapper/SKILL.md",
              "---\nname: mapper\ndescription: Map a network. Then draw it.\n---\n")
        write(root / "skills/net/mapper/shared.md", "shared\n")
        write(root / "skills/net/mapper/scripts/tool.py", "copied\n")
        write(root / "harness/tool.py", "copied\n")
        write(root / "skills/shared.json", json.dumps({
            "_why": {"skills/ops/fixer/shared.md": "a note, not a source"},
            "skills/ops/fixer/shared.md": ["skills/net/mapper/shared.md"],
            "harness/tool.py": ["skills/net/mapper/scripts/tool.py"]}))
        write(root / "evals/scores.json", json.dumps({"evals": {
            "eval-3-fix-crash": {"skill": "fixer", "iteration": "iteration-9", "n": 3,
                                 "staging": "harness", "skill_hash": "a", "date": "2026-11-18",
                                 "date_from": "run.json mtime", "delta_mean": 0.952, "cap_mean": 1.0},
            "eval-12-fix-again": {"skill": "fixer", "iteration": "iteration-10", "n": 3,
                                  "staging": "standalone", "skill_hash": "b", "date": "2026-11-20",
                                  "date_from": "run.json finished", "delta_mean": 1.0, "cap_mean": 0.5}}}))
        write(root / "CHANGELOG.md",
              "# Changelog\n\n## [Unreleased]\n\n## [1.2.0] - 2026-11-21\n\n## [1.1.0] - 2026-11-01\n")
        write(root / ".github/CODEOWNERS", "* @someone\n/skills/net/ @net-team # networking\n")

    def skills(self):
        return {s["name"]: s for s in registry.build(self.root)}

    def test_fields_derive_from_frontmatter_scores_changelog_and_codeowners(self):
        s = self.skills()
        fixer, mapper = s["fixer"], s["mapper"]
        self.assertEqual(fixer["family"], "ops")
        self.assertEqual(fixer["purpose"], "Fix a bug, e.g. a crash.")
        self.assertEqual(mapper["purpose"], "Map a network.")
        self.assertEqual((fixer["owner"], mapper["owner"]), ("someone", "net-team"))
        self.assertEqual(registry.version(self.root), "1.2.0")
        self.assertEqual(fixer["dependencies"],
                         {"copied_from": {}, "scripts": ["scripts/probe.py"], "harness": True})
        self.assertEqual(mapper["dependencies"],
                         {"copied_from": {"fixer": ["shared.md"], "harness/": ["scripts/tool.py"]},
                          "scripts": [], "harness": False})
        self.assertEqual(fixer["last_eval"], "2026-11-20")
        self.assertEqual([e["id"] for e in fixer["evals"]], [3, 12])
        self.assertIsNone(mapper["last_eval"])

        md = registry.render(self.root)["skills/REGISTRY.md"]
        self.assertIn("| [fixer](ops/fixer/SKILL.md) | ops | Fix a bug, e.g. a crash. | someone | 1.2.0 "
                      "| scripts: scripts/probe.py; harness/ (scored with it) | 2026-11-20 "
                      "| 3: 0.95 / 1.00<br>12: 1.00 / 0.50 |", md)
        self.assertIn("| [mapper](net/mapper/SKILL.md) | net | Map a network. | net-team | 1.2.0 "
                      "| copies from fixer: shared.md; copies from harness/: scripts/tool.py | — | — |", md)
        # Sorted by family, then name.
        self.assertLess(md.index("[mapper]"), md.index("[fixer]"))

    def test_defaults_without_changelog_or_codeowners(self):
        (self.root / "CHANGELOG.md").unlink()
        (self.root / ".github/CODEOWNERS").unlink()
        self.assertEqual(registry.version(self.root), "unreleased")
        self.assertEqual(self.skills()["fixer"]["owner"], registry.DEFAULT_OWNER)

    def check(self):
        return subprocess.run([sys.executable, str(SCRIPT), "--check", "--root", str(self.root)],
                              capture_output=True, text=True)

    def test_check_passes_when_fresh_and_fails_with_the_command_when_stale(self):
        missing = self.check()
        self.assertEqual(missing.returncode, 1)
        subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root)],
                       check=True, capture_output=True)
        self.assertEqual(self.check().returncode, 0, self.check().stdout)

        # A new score makes the committed registry stale.
        scores = json.loads((self.root / "evals/scores.json").read_text())
        scores["evals"]["eval-3-fix-crash"]["delta_mean"] = 0.5
        (self.root / "evals/scores.json").write_text(json.dumps(scores))
        stale = self.check()
        self.assertEqual(stale.returncode, 1)
        self.assertIn("skills/REGISTRY.md: stale", stale.stdout)
        self.assertIn("python3 .github/scripts/registry.py", stale.stdout)


if __name__ == "__main__":
    unittest.main()
