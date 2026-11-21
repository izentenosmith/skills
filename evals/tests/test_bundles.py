"""The bundles check: skills/bundles.json against the skills that exist and the
install lines README.md shows for them.
Run: python3 -m unittest discover evals/tests"""
import copy
import json
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / ".github/scripts"))

import bundles  # noqa: E402

SKILLS = {"a", "b", "c", "d", "memo"}
MANIFEST = {
    "with_every_bundle": ["memo"],
    "bundles": {
        "one": {"description": "x", "families": ["f"], "skills": ["a", "b"], "placed": {"b": "why"}},
        "two": {"description": "y", "families": ["g"], "skills": ["c", "d"], "placed": {}},
    },
}
INSTALL = "npx skills add izentenosmith/skills --skill"
README = f"""# Repo

### Bundles

Some prose.

```bash
# one — the first
{INSTALL} a b memo

# two — the second
{INSTALL} c d memo
```

**Everything:**

```bash
{INSTALL} '*'
```

## Next
"""


def run(manifest=MANIFEST, skills=SKILLS, readme=README):
    return bundles.check(manifest, skills, readme)


def edited(fn):
    m = copy.deepcopy(MANIFEST)
    fn(m)
    return m


class Bundles(unittest.TestCase):
    def assertOne(self, problems, text):
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(text, problems[0])

    def test_clean(self):
        self.assertEqual(run(), [])
        self.assertEqual(run(json.dumps(MANIFEST)), [])

    def test_the_repo_is_clean(self):
        names = {p.parent.name for p in (REPO / "skills").glob("*/*/SKILL.md")}
        self.assertEqual(bundles.check((REPO / "skills/bundles.json").read_text(), names,
                                       (REPO / "README.md").read_text()), [])

    def test_unparsable(self):
        self.assertOne(run("{not json"), "does not parse")

    def test_no_bundles(self):
        self.assertOne(run({"bundles": {}}), "no bundles")

    def test_bundle_without_skills(self):
        problems = run(edited(lambda m: m["bundles"]["two"].update(skills=[])))
        self.assertIn("bundle 'two' has no skills", problems[0])

    def test_unknown_skill(self):
        problems = run(edited(lambda m: m["bundles"]["one"]["skills"].append("zzz")))
        self.assertTrue(any("'zzz', which no SKILL.md defines" in p for p in problems), problems)

    def test_unknown_extra(self):
        problems = run(skills=SKILLS - {"memo"})
        self.assertTrue(any("with_every_bundle names 'memo'" in p for p in problems), problems)

    def test_skill_in_no_bundle(self):
        self.assertOne(run(skills=SKILLS | {"e"}), "e is in no bundle")

    def test_extra_counts_as_covered(self):
        self.assertEqual(run(skills=SKILLS), [])

    def test_over_twenty_counting_the_extra(self):
        names = [f"s{i}" for i in range(20)]
        m = edited(lambda m: m["bundles"]["one"].update(skills=names, placed={}))
        readme = README.replace(f"{INSTALL} a b memo", f"{INSTALL} {' '.join(names)} memo")
        problems = run(m, SKILLS - {"a", "b"} | set(names), readme)
        self.assertOne(problems, "installs 21 skills")

    def test_twenty_counting_the_extra_is_fine(self):
        names = [f"s{i}" for i in range(19)]
        m = edited(lambda m: m["bundles"]["one"].update(skills=names, placed={}))
        readme = README.replace(f"{INSTALL} a b memo", f"{INSTALL} {' '.join(names)} memo")
        self.assertEqual(run(m, SKILLS - {"a", "b"} | set(names), readme), [])

    def test_duplicate_in_a_bundle(self):
        m = edited(lambda m: m["bundles"]["one"]["skills"].append("a"))
        self.assertTrue(any("lists 'a' more than once" in p for p in run(m)))

    def test_placed_reason_for_an_unlisted_skill(self):
        m = edited(lambda m: m["bundles"]["one"]["placed"].update(c="why"))
        self.assertOne(run(m), "placed reason for 'c'")

    def test_no_bundles_section(self):
        self.assertOne(run(readme=README.replace("### Bundles", "### Other")), "no `### Bundles` section")

    def test_bundle_without_readme_line(self):
        readme = README.replace(f"# two — the second\n{INSTALL} c d memo\n", "")
        self.assertOne(run(readme=readme), "no `# two` comment")

    def test_install_line_without_its_comment(self):
        readme = README.replace("# two — the second\n", "")
        problems = run(readme=readme)
        self.assertTrue(any("no `# two` comment" in p for p in problems), problems)

    def test_readme_line_differs(self):
        self.assertOne(run(readme=README.replace(f"{INSTALL} c d memo", f"{INSTALL} c memo")),
                       "the two install line installs c memo")

    def test_readme_line_missing_the_extra(self):
        self.assertOne(run(readme=README.replace(f"{INSTALL} c d memo", f"{INSTALL} c d")),
                       "the two install line")

    def test_readme_line_for_unknown_bundle(self):
        readme = README.replace("```\n\n**Everything", f"\n# three\n{INSTALL} a memo\n```\n\n**Everything")
        self.assertOne(run(readme=readme), "install line for 'three'")


if __name__ == "__main__":
    unittest.main()
