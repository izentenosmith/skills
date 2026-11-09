"""memlint.py (skills/memory/repo-memory/scripts): every audit code on a hand-built .memory/ tree, the
dream delta on a small git history, and the CLI's exit codes.
Run: python3 -m unittest discover harness/tests"""
import contextlib
import datetime
import importlib.util
import io
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import textwrap
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE.parent.parent / "skills/memory/repo-memory/scripts/memlint.py"
spec = importlib.util.spec_from_file_location("memlint", SCRIPT)
ML = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ML)

TODAY = datetime.date(2026, 11, 7)
GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="T",
               GIT_COMMITTER_EMAIL="t@example.invalid", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


def note(name, description, source="src/app.py", verified="2026-11-01", volatility="low", type="fact", body=""):
    return textwrap.dedent(f"""\
        ---
        name: {name}
        description: {description}
        type: {type}
        source: {source}
        verified: {verified}
        volatility: {volatility}
        ---

        """) + (body or f"{description}.\n")


INDEX = "# Repository memory\n\nPurpose.\n\n## Facts\n- [A](notes/alpha.md) — a\n"


class Tree(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="memlint-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "src").mkdir()
        (self.root / "src/app.py").write_text("MAX_RETRIES = 5\n\ndef send():\n    pass\n")
        self.w(".memory/INDEX.md", INDEX)
        self.w(".memory/notes/alpha.md", note("alpha", "send retries five times before giving up",
                                              body="`src/app.py::send` retries `MAX_RETRIES` times.\n"))

    def w(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, env=GIT_ENV)

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-qm", msg)
        return subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()

    def codes(self):
        findings, _ = ML.audit(ML.Memory(self.root), TODAY)
        return sorted({f["code"] for f in findings}), findings


class Audit(Tree):
    def test_clean_tree_has_no_errors_or_warnings(self):
        codes, findings = self.codes()
        self.assertEqual([c for c in codes if ML.SEVERITY[c] != "info"], [], findings)

    def test_ml01_no_memory_and_no_index(self):
        shutil.rmtree(self.root / ".memory")
        self.assertEqual(self.codes()[0], ["ML01"])
        self.w(".memory/notes/alpha.md", note("alpha", "x"))
        self.assertIn("ML01", self.codes()[0])

    def test_ml02_index_over_200_lines_or_25kb(self):
        self.w(".memory/INDEX.md", INDEX + "".join(f"- line {i}\n" for i in range(200)))
        self.assertIn("ML02", self.codes()[0])
        self.w(".memory/INDEX.md", INDEX + "x" * 26 * 1024 + "\n")
        self.assertIn("ML02", self.codes()[0])

    def test_ml03_frontmatter_problems(self):
        self.w(".memory/notes/beta.md", "no frontmatter\n")
        self.w(".memory/notes/gamma.md", note("wrong-name", "g"))
        self.w(".memory/notes/delta.md", note("delta", "d", type="musing", volatility="medium", verified="last week"))
        self.w(".memory/wiki/page.md", note("page", "p", type="fact"))
        self.w(".memory/INDEX.md", INDEX + "- [b](notes/beta.md)\n- [g](notes/gamma.md)\n- [d](notes/delta.md)\n"
                                           "- [p](wiki/page.md)\n")
        _, findings = self.codes()
        ml03 = [f for f in findings if f["code"] == "ML03"]
        whats = " ".join(f["what"] for f in ml03)
        for part in ("no frontmatter", "does not match the file name", "'musing'", "'medium'",
                     "not a YYYY-MM-DD", "pages are type: entity"):
            self.assertIn(part, whats)

    def test_ml04_broken_wikilink_and_markdown_link(self):
        self.w(".memory/notes/alpha.md", note("alpha", "a", body="See [[nowhere]] and [x](../wiki/missing.md).\n"))
        broken = [f for f in self.codes()[1] if f["code"] == "ML04"]
        self.assertEqual(len(broken), 2, broken)

    def test_links_inside_fences_are_examples(self):
        self.w(".memory/notes/alpha.md", note("alpha", "a", body="```\n[[nowhere]] `src/gone.py`\n```\n"))
        self.assertNotIn("ML04", self.codes()[0])
        self.assertNotIn("ML05", self.codes()[0])

    def test_ml05_missing_file_missing_symbol_and_line_past_end(self):
        self.w(".memory/notes/alpha.md", note("alpha", "a", body="`src/gone.py`, `src/app.py::resend`, `src/app.py:99`, "
                                                                 "`src/app.py:2` and `src/app.py::send` are fine.\n"))
        whats = [f["what"] for f in self.codes()[1] if f["code"] == "ML05"]
        self.assertEqual(len(whats), 3, whats)
        self.assertTrue(any("no such file" in w for w in whats))
        self.assertTrue(any("`resend` does not appear" in w for w in whats))
        self.assertTrue(any("has 5 lines" in w for w in whats))

    def test_a_bare_file_name_resolves_when_one_file_has_it(self):
        self.w(".memory/notes/alpha.md", note("alpha", "a", body="`app.py::send` and `app.py:2`; `nowhere.py` is not.\n"))
        whats = [f["what"] for f in self.codes()[1] if f["code"] == "ML05"]
        self.assertEqual(whats, ["`nowhere.py`: no such file"])

    def test_paths_outside_the_repo_are_not_references(self):
        self.w(".memory/notes/alpha.md", note("alpha", "a", body="In the vault at `kv/app/staging/db`; bucket `exports/daily`.\n"))
        self.assertNotIn("ML05", self.codes()[0])

    def test_ml05_unknown_commit_in_source(self):
        self.git("init", "-q", "-b", "main")
        self.commit("init")
        self.w(".memory/notes/alpha.md", note("alpha", "a", source="commit deadbeef1"))
        self.assertIn("ML05", self.codes()[0])

    def test_ml06_secrets_reported_without_the_value(self):
        self.w(".memory/notes/alpha.md", note("alpha", "a", body="DB: postgres://app:Hunter2pass@db.internal/app\n"
                                                                 "api_key = abc123def456ghi\n"))
        secrets = [f for f in self.codes()[1] if f["code"] == "ML06"]
        self.assertEqual(len(secrets), 2, secrets)
        dump = json.dumps(secrets)
        self.assertNotIn("Hunter2pass", dump)
        self.assertNotIn("abc123def456ghi", dump)

    def test_ml06_ignores_where_a_secret_lives(self):
        self.w(".memory/notes/alpha.md", note("alpha", "a", body="password: stored in vault kv/app/db\n"))
        self.assertNotIn("ML06", self.codes()[0])

    def test_ml07_orphan_and_reachability_through_pages(self):
        self.w(".memory/notes/lonely.md", note("lonely", "nobody links this one"))
        self.w(".memory/wiki/sms.md", note("sms", "the sms provider page", type="entity"))
        self.w(".memory/notes/linked.md", note("linked", "reached only through the page"))
        self.w(".memory/notes/alpha.md", note("alpha", "a", body="See [[sms]].\n"))
        self.w(".memory/wiki/sms.md", note("sms", "the sms provider page", type="entity", body="[[linked]]\n"))
        orphans = [f["where"] for f in self.codes()[1] if f["code"] == "ML07"]
        self.assertEqual(orphans, [".memory/notes/lonely.md"])

    def test_ml08_stale_by_volatility(self):
        self.w(".memory/notes/alpha.md", note("alpha", "a", verified="2026-09-01", volatility="high"))
        self.assertIn("ML08", self.codes()[0])
        self.w(".memory/notes/alpha.md", note("alpha", "a", verified="2026-09-01", volatility="low"))
        self.assertNotIn("ML08", self.codes()[0])

    def test_ml09_duplicates_by_description_and_body(self):
        self.w(".memory/notes/twin.md", note("twin", "send retries five times before it gives up"))
        self.w(".memory/INDEX.md", INDEX + "- [t](notes/twin.md)\n")
        self.assertIn("ML09", self.codes()[0])

    def test_ml10_oversized_note(self):
        self.w(".memory/notes/alpha.md", note("alpha", "a", body="line\n" * 41))
        self.assertIn("ML10", self.codes()[0])

    def test_ml11_symlink_out_of_memory(self):
        (self.root / "outside.md").write_text("x\n")
        (self.root / ".memory/notes/link.md").symlink_to(self.root / "outside.md")
        self.assertIn("ML11", self.codes()[0])


class Delta(Tree):
    def test_delta_ties_commits_to_the_notes_they_touch(self):
        self.git("init", "-q", "-b", "main")
        (self.root / "src/other.py").write_text("x = 1\n")
        base = self.commit("initial")
        self.w(".memory/.dream-state", f"watermark: {base}\ndreamed: 2026-11-01\n")
        self.commit("dream")
        (self.root / "src/app.py").write_text("MAX_RETRIES = 7\n\ndef send():\n    pass\n")
        self.commit("raise retries to 7")
        (self.root / "src/other.py").write_text("x = 2\n")
        self.w(".memory/notes/fresh.md", note("fresh", "captured in a session", source="session 2026-11-05"))
        self.commit("other change and a capture")
        d = ML.delta(ML.Memory(self.root), TODAY)
        self.assertEqual(d["since"], 3)
        self.assertEqual([r["file"] for r in d["reverify"]], [".memory/notes/alpha.md"])
        self.assertEqual(d["reverify"][0]["why"][0]["path"], "src/app.py")
        self.assertEqual(d["captured"], [".memory/notes/fresh.md"])
        self.assertIn("raise retries to 7", ML.md_delta(d))

    def test_no_watermark_means_verify_everything(self):
        self.git("init", "-q", "-b", "main")
        self.commit("initial")
        d = ML.delta(ML.Memory(self.root), TODAY)
        self.assertIsNone(d["since"])
        self.assertEqual(d["reverify"][0]["why"], "first dream: verify every note")

    def test_ml12_dream_due_after_enough_commits(self):
        self.git("init", "-q", "-b", "main")
        base = self.commit("initial")
        self.w(".memory/.dream-state", f"watermark: {base}\ndreamed: 2026-11-06\n")
        for i in range(ML.DREAM_DUE_COMMITS):
            (self.root / "src/other.py").write_text(f"x = {i}\n")
            self.commit(f"c{i}")
        self.assertIn("ML12", self.codes()[0])

    def test_unreachable_watermark_is_a_first_pass(self):
        self.git("init", "-q", "-b", "main")
        self.commit("initial")
        self.w(".memory/.dream-state", "watermark: 0123456789abcdef0123456789abcdef01234567\ndreamed: 2026-11-01\n")
        info = ML.dream_info(ML.Memory(self.root), TODAY)
        self.assertIn("not an ancestor", info["due"])


class Cli(Tree):
    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = ML.main([*args, "--root", str(self.root), "--today", "2026-11-07"])
        return code, out.getvalue()

    def test_exit_codes_and_json(self):
        code, text = self.run_cli("audit")
        self.assertEqual(code, 0, text)
        self.assertIn("**Result:** 0 errors", text)
        self.w(".memory/notes/alpha.md", note("alpha", "a", body="[[gone]]\n"))
        js = self.root / "out.json"
        code, _ = self.run_cli("audit", "--json", str(js))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(js.read_text())["findings"][0]["code"], "ML04")

    def test_usage_errors(self):
        self.assertEqual(ML.main(["audit", "--root", str(self.root / "nope")]), 2)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ML.main(["audit", "--root", str(self.root), "--today", "soon"]), 2)

    def test_read_only(self):
        self.git("init", "-q", "-b", "main")
        self.commit("initial")
        before = subprocess.run(["git", "-C", str(self.root), "status", "--porcelain"], capture_output=True,
                                text=True).stdout
        self.run_cli("audit")
        self.run_cli("delta")
        after = subprocess.run(["git", "-C", str(self.root), "status", "--porcelain"], capture_output=True,
                               text=True).stdout
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
