"""The authoring-guide checks check_repo.py runs on skill folders
(.github/scripts/authoring.py). Run: python3 -m unittest discover evals/tests"""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".github/scripts"))

import authoring  # noqa: E402

SKILL = """---
name: demo
description: Turns a plan into tests. Use when asked for "tests".
---
# demo

**Requires:** `git`.

## Reference files

- [long.md](long.md) — open it when you need the details.
- [short.md](short.md) — open it when a run stops.

## Steps

Run it; see [long.md](long.md#alpha).
"""


def long_ref(toc=True, sections=("Alpha", "Beta gamma")):
    head = "# Long\n\nIntro.\n\n"
    if toc:
        head += "## Contents\n\n" + "".join(f"- [{s}](#{authoring.slug(s)})\n" for s in sections) + "\n"
    body = "".join(f"## {s}\n\n" + "line\n" * 60 for s in sections)
    return head + body


class Description(unittest.TestCase):
    def test_third_person_verb_passes(self):
        self.assertEqual(authoring.description_problems('Adjudicates the findings. Use after "x".'), [])
        self.assertEqual(authoring.description_problems("Runs a staff-architect review for CI."), [])

    def test_imperative_or_noun_opening_fails(self):
        for desc in ("Turn the plan into tests.", "Use when asked.", "Stage 5 of the pipeline.",
                     "Test-driven development via the loop."):
            self.assertTrue(authoring.description_problems(desc), desc)

    def test_second_or_first_person_fails(self):
        self.assertTrue(authoring.description_problems("Turns plans into tests you can run."))
        self.assertTrue(authoring.description_problems("Turns plans into tests I write."))


class DescriptionBudget(unittest.TestCase):
    def test_at_and_under_the_budget_pass(self):
        for n in (1, authoring.DESCRIPTION_BUDGET - 1, authoring.DESCRIPTION_BUDGET):
            self.assertEqual(authoring.description_length_problems("x" * n), [], n)

    def test_over_the_budget_fails(self):
        msgs = authoring.description_length_problems("x" * (authoring.DESCRIPTION_BUDGET + 1))
        self.assertEqual(len(msgs), 1)
        self.assertIn(f"budget {authoring.DESCRIPTION_BUDGET}", msgs[0])

    def test_over_the_hard_limit_names_it(self):
        msgs = authoring.description_length_problems("x" * (authoring.DESCRIPTION_HARD_LIMIT + 1))
        self.assertEqual(len(msgs), 1)
        self.assertIn(str(authoring.DESCRIPTION_HARD_LIMIT), msgs[0])

    def test_measured_on_the_parsed_scalar_not_the_quoted_text(self):
        # 500 characters once parsed; 504 as written, with its quotes and backslash escapes.
        value = 'Turns "x' + "y" * 491 + '"'
        raw = '"' + value.replace('"', '\\"') + '"'
        parsed, why = authoring.yaml_scalar(raw)
        self.assertIsNone(why)
        self.assertEqual(parsed, value)
        self.assertEqual(len(parsed), authoring.DESCRIPTION_BUDGET)
        self.assertGreater(len(raw), authoring.DESCRIPTION_BUDGET)
        self.assertEqual(authoring.description_length_problems(parsed), [])
        self.assertTrue(authoring.description_length_problems(parsed + "z"))

    def test_single_quoted_scalar_unescapes_doubled_quotes(self):
        self.assertEqual(authoring.yaml_scalar("'it''s'"), ("it's", None))

    def test_unquoted_colon_space_is_rejected(self):
        self.assertIsNotNone(authoring.yaml_scalar("Runs a review: then stops.")[1])


class Contents(unittest.TestCase):
    def test_short_file_needs_none(self):
        self.assertEqual(authoring.toc_problems("# x\n\n## A\n\ntext\n"), [])

    def test_long_file_with_full_contents_passes(self):
        self.assertEqual(authoring.toc_problems(long_ref()), [])

    def test_long_file_without_contents_fails(self):
        self.assertTrue(authoring.toc_problems(long_ref(toc=False)))

    def test_missing_and_dangling_entries_fail(self):
        text = long_ref().replace("- [Beta gamma](#beta-gamma)\n", "- [Delta](#delta)\n")
        msgs = authoring.toc_problems(text)
        self.assertTrue(any("#beta-gamma" in m for m in msgs))
        self.assertTrue(any("#delta" in m for m in msgs))

    def test_headings_in_fences_are_not_sections(self):
        text = long_ref() + "```markdown\n## Iteration 1\n```\n"
        self.assertEqual(authoring.toc_problems(text), [])

    def test_slug_matches_github(self):
        self.assertEqual(authoring.slug("env.md — how to run this repo"), "envmd--how-to-run-this-repo")
        self.assertEqual(authoring.slug("The verdict is computed, not chosen"), "the-verdict-is-computed-not-chosen")


class ReferenceIndex(unittest.TestCase):
    def test_every_reference_listed_with_when(self):
        self.assertEqual(authoring.reference_index_problems(SKILL, {"long.md", "short.md"}), [])

    def test_unlisted_reference_fails(self):
        msgs = authoring.reference_index_problems(SKILL, {"long.md", "short.md", "extra.md"})
        self.assertEqual(len(msgs), 1)
        self.assertIn("extra.md", msgs[0])

    def test_inline_link_elsewhere_does_not_count(self):
        text = SKILL.replace("- [long.md](long.md) — open it when you need the details.\n", "")
        self.assertTrue(authoring.reference_index_problems(text, {"long.md", "short.md"}))

    def test_line_without_when_fails(self):
        text = SKILL.replace("open it when a run stops", "the stop rules")
        msgs = authoring.reference_index_problems(text, {"long.md", "short.md"})
        self.assertEqual(len(msgs), 1)
        self.assertIn("short.md", msgs[0])

    def test_missing_section_fails(self):
        self.assertTrue(authoring.reference_index_problems("# x\n", {"a.md"}))


class Links(unittest.TestCase):
    def test_reference_to_reference_link_fails(self):
        msgs = authoring.reference_link_problems("see [b](b.md#x) and [skill](SKILL.md#y)", {"b.md"})
        self.assertEqual(len(msgs), 1)
        self.assertIn("b.md", msgs[0])

    def test_mentions_in_backticks_pass(self):
        self.assertEqual(authoring.reference_link_problems("see `b.md` and `[b](b.md)`", {"b.md"}), [])

    def test_sibling_skill_link_fails(self):
        folder = pathlib.Path("/repo/skills/development/tdd")
        here = folder / "SKILL.md"
        self.assertTrue(authoring.escaping_link_problems("[x](../agent-brief/SKILL.md)", folder, here))
        self.assertEqual(authoring.escaping_link_problems("[x](mocking.md) [y](#a)", folder, here), [])


class Folder(unittest.TestCase):
    def test_check_skill_on_a_clean_and_a_broken_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = pathlib.Path(tmp) / "demo"
            folder.mkdir()
            (folder / "SKILL.md").write_text(SKILL)
            (folder / "long.md").write_text(long_ref())
            (folder / "short.md").write_text("# Short\n\nSee [SKILL.md](SKILL.md).\n")
            self.assertEqual(authoring.check_skill(folder), [])

            (folder / "short.md").write_text("# Short\n\nSee [long.md](long.md) and [t](../tdd/SKILL.md).\n")
            (folder / "SKILL.md").write_text(SKILL.replace("Turns a plan", "Turn a plan"))
            files = sorted(f for f, _ in authoring.check_skill(folder))
            self.assertEqual(files, ["SKILL.md", "short.md", "short.md"])


if __name__ == "__main__":
    unittest.main()
