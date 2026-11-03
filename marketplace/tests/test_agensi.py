"""agensi.py against a small skills tree. Run: python3 -m unittest discover marketplace/tests"""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import agensi as AG  # noqa: E402


def skill(root, family, name, body, desc="Does a thing. Use when a thing needs doing.", **docs):
    folder = root / "skills" / family / name
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n\n{body}\n")
    for doc, text in docs.items():
        (folder / f"{doc}.md").write_text(text)
    return folder


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args)


class Tree(unittest.TestCase):
    """A repo with two families, a symlinked doc, and a harness folder."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        (self.root / "harness").mkdir()
        (self.root / "harness" / "flow.py").write_text("")
        (self.root / "skills" / "ops").mkdir(parents=True)
        (self.root / "skills" / "ops" / "README.md").write_text("# ops\n")
        skill(self.root, "db", "audit", "Audit.", theory="# Theory\n\nSee [lenses](lenses.md).\n",
              lenses="# Lenses\n\nPer [theory](theory.md) §2.\n")
        self.query = skill(
            self.root, "db", "query",
            "Settles what [audit](../audit/SKILL.md) flags, per [lenses](../audit/lenses.md#views).\n"
            "The coordinator is [flow.py](../../../harness/flow.py). Back to [the family](../../ops/README.md).\n"
            "Literal: `[audit](../audit/SKILL.md)`\n\n```\n[x](../audit/SKILL.md)\n```",
            rubric="# Rubric\n\nScored per [theory](theory.md).\n")
        (self.query / "theory.md").symlink_to("../audit/theory.md")
        self.patches = {}
        (self.root / "patches.json").write_text("{}")
        (self.root / "bundles.json").write_text("{}")
        for attr, value in (("ROOT", self.root), ("SKILLS", self.root / "skills"),
                            ("PATCHES", self.root / "patches.json"),
                            ("BUNDLES", self.root / "bundles.json")):
            original = getattr(AG, attr)
            setattr(AG, attr, value)
            self.addCleanup(setattr, AG, attr, original)

    def build(self, name="query"):
        """The one package in a single-skill listing, checked."""
        listing = AG.build_listing(name, [name], AG.discover(AG.SKILLS), self.patches)
        pkg = listing.packages[0]
        pkg.problems = listing.all_problems()
        return pkg


class Rewrite(Tree):
    def test_symlinked_doc_becomes_a_real_file(self):
        pkg = self.build()
        self.assertEqual(pkg.files["theory.md"], (self.root / "skills/db/audit/theory.md").read_text())
        self.assertEqual(pkg.problems, [])

    def test_another_skills_doc_is_copied_with_what_it_links_to(self):
        pkg = self.build()
        self.assertIn("[lenses](lenses.md#views)", pkg.files["SKILL.md"])
        self.assertEqual(pkg.vendored, {"lenses.md": "skills/db/audit/lenses.md"})
        # lenses.md links to theory.md, which the package already ships as the symlink
        self.assertIn("[theory](theory.md)", pkg.files["lenses.md"])

    def test_another_skill_becomes_its_name_and_is_listed(self):
        pkg = self.build()
        self.assertIn("Settles what `audit` flags", pkg.files["SKILL.md"])
        self.assertEqual(pkg.related, {"audit"})
        self.assertIn("## Related skills", pkg.files["SKILL.md"])

    def test_links_outside_the_skills_become_their_text(self):
        pkg = self.build()
        self.assertIn("The coordinator is flow.py. Back to the family.", pkg.files["SKILL.md"])
        self.assertEqual(len(pkg.demoted), 2)

    def test_code_is_left_alone(self):
        text = self.build().files["SKILL.md"]
        self.assertIn("`[audit](../audit/SKILL.md)`", text)
        self.assertIn("```\n[x](../audit/SKILL.md)\n```", text)

    def test_a_skill_with_no_neighbours_gets_no_related_section(self):
        self.assertNotIn("Related skills", self.build("audit").files["SKILL.md"])


class Patches(Tree):
    def test_patch_applies_before_links_are_rewritten(self):
        self.patches = {"query": {"SKILL.md": [
            {"old": "The coordinator is [flow.py](../../../harness/flow.py). ", "new": ""}]}}
        pkg = self.build()
        self.assertIn("flags, per [lenses](lenses.md#views).\nBack to the family.", pkg.files["SKILL.md"])
        self.assertEqual(pkg.problems, [])

    def test_a_patch_that_no_longer_matches_fails(self):
        self.patches = {"query": {"SKILL.md": [{"old": "text that is gone", "new": ""}]}}
        self.assertIn("matches 0 times", " ".join(self.build().problems))

    def test_a_patch_for_a_missing_file_fails(self):
        self.patches = {"query": {"nope.md": [{"old": "x", "new": ""}]}}
        self.assertIn("not in the package", " ".join(self.build().problems))


class Checks(Tree):
    def test_secret_looking_strings_fail(self):
        (self.query / "rubric.md").write_text("ENV API_KEY=sk-live-...\n")
        problems = " ".join(self.build().problems)
        self.assertIn("rubric.md:1", problems)
        self.assertIn("secret scanner", problems)

    def test_detection_patterns_are_not_secrets(self):
        (self.query / "rubric.md").write_text("grep -nE 'AKIA[0-9A-Z]{16}|-----BEGIN (RSA|EC) PRIVATE KEY'\n")
        self.assertEqual(self.build().problems, [])

    def test_name_must_match_folder(self):
        md = self.query / "SKILL.md"
        md.write_text(md.read_text().replace("name: query", "name: queries"))
        self.assertIn("does not match the folder", " ".join(self.build().problems))

    def test_a_link_that_does_not_resolve_fails(self):
        (self.query / "rubric.md").write_text("See [gone](gone.md).\n")
        self.assertIn("does not resolve inside the zip (gone.md)", " ".join(self.build().problems))

    def test_harness_mentions_are_warnings_not_problems(self):
        (self.query / "rubric.md").write_text("When the harness is available, run it. A throwaway harness is fine.\n")
        pkg = self.build()
        self.assertEqual(pkg.problems, [])
        self.assertEqual(pkg.warnings, ["rubric.md (1)"])


class Zips(Tree):
    def test_zip_holds_the_skill_folder_and_is_reproducible(self):
        skills = AG.discover(AG.SKILLS)
        first, second = (AG.zip_bytes(AG.build_listing("query", ["query"], skills, {})) for _ in range(2))
        self.assertEqual(first, second)
        with zipfile.ZipFile(io.BytesIO(first)) as zf:
            self.assertIn("query/SKILL.md", zf.namelist())
            self.assertTrue(all(i.date_time == AG.ZIP_DATE for i in zf.infolist()))

    def test_main_writes_zips_and_reports_what_changed(self):
        out = self.root / "dist"
        self.assertEqual(quiet(AG.main, ["--out", str(out)]), 0)
        self.assertEqual(sorted(p.name for p in out.glob("*.zip")), ["audit.zip", "query.zip"])
        manifest = json.loads((out / "manifest.json").read_text())["listings"]
        self.assertEqual(manifest["query"]["skills"]["query"]["related"], ["audit"])
        self.assertEqual(manifest["query"]["price_usd"], 5)

        (self.query / "rubric.md").write_text("# Rubric, revised\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            AG.main(["--out", str(out)])
        lines = {line.split()[0]: line.split()[-1] for line in buf.getvalue().splitlines()[1:] if line.strip()}
        self.assertEqual((lines["audit"], lines["query"]), ("unchanged", "changed"))

    def test_check_writes_nothing_and_a_problem_fails_the_run(self):
        out = self.root / "dist"
        (self.query / "rubric.md").write_text("ENV API_KEY=sk-live-...\n")
        self.assertEqual(quiet(AG.main, ["--out", str(out), "--check"]), 1)
        self.assertEqual(quiet(AG.main, ["--out", str(out)]), 1)
        self.assertFalse(out.exists())

    def test_unknown_skill_is_a_usage_error(self):
        self.assertEqual(quiet(AG.main, ["nope"]), 2)


class Bundles(Tree):
    def bundle(self):
        return AG.build_listing("db-pack", ["audit", "query"], AG.discover(AG.SKILLS), {})

    def test_links_between_members_stay_live(self):
        listing = self.bundle()
        query = next(p for p in listing.packages if p.name == "query")
        self.assertIn("Settles what [audit](../audit/SKILL.md) flags", query.files["SKILL.md"])
        self.assertIn("[lenses](../audit/lenses.md#views)", query.files["SKILL.md"])
        self.assertEqual(query.vendored, {})
        self.assertNotIn("Related skills", query.files["SKILL.md"])
        self.assertEqual(listing.all_problems(), [])

    def test_a_bundle_costs_ten_dollars_whatever_its_size(self):
        self.assertEqual((self.bundle().kind, self.bundle().price_usd), ("bundle", 10))
        three = AG.Listing("trio", [AG.Package(n) for n in ("a", "b", "c")])
        self.assertEqual(three.price_usd, 10)
        self.assertEqual(AG.Listing("solo", [AG.Package("a")]).price_usd, 5)

    def test_bundle_zips_every_member(self):
        listing = self.bundle()
        with zipfile.ZipFile(io.BytesIO(AG.zip_bytes(listing))) as zf:
            self.assertTrue({"audit/SKILL.md", "query/SKILL.md"} <= set(zf.namelist()))

    def test_main_builds_bundles_from_bundles_json(self):
        (self.root / "bundles.json").write_text(json.dumps({"db-pack": ["audit", "query"]}))
        out = self.root / "dist"
        self.assertEqual(quiet(AG.main, ["--out", str(out)]), 0)
        manifest = json.loads((out / "manifest.json").read_text())["listings"]
        self.assertEqual({k: v["price_usd"] for k, v in manifest.items()},
                         {"audit": 5, "query": 5, "db-pack": 10})

    def test_a_bad_bundle_fails_the_run(self):
        for bad in ({"db-pack": ["audit", "nope"]}, {"db-pack": ["audit"]}, {"query": ["audit", "query"]}):
            (self.root / "bundles.json").write_text(json.dumps(bad))
            self.assertEqual(quiet(AG.main, ["--check"]), 1, bad)


class ThisRepo(unittest.TestCase):
    def test_every_skill_packages_cleanly(self):
        self.assertEqual(quiet(AG.main, ["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
