"""redgreen.py against throwaway git repos. Run: python3 -m unittest discover harness/tests"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import redgreen as R  # noqa: E402

# Every test file is a plain script: it exits non-zero when an assertion fails.
CMD = 'for f in tests/test_*.py; do PYTHONPATH=. python3 "$f" || exit 1; done'
BUGGY = "def total(xs):\n    return sum(round(x) for x in xs)\n"
FIXED = "def total(xs):\n    return round(sum(xs))\n"
GOOD_TEST = "from calc import total\nassert total([0.4, 0.4, 0.4]) == 1, total([0.4, 0.4, 0.4])\n"
VACUOUS_TEST = "from calc import total\nassert total([1, 2]) == 3\n"


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo,
                          check=True, capture_output=True, text=True).stdout.strip()


class RedGreen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.tmp.name) / "r"
        (self.repo / "tests").mkdir(parents=True)
        (self.repo / "calc.py").write_text(BUGGY)
        (self.repo / "tests" / "test_existing.py").write_text("assert True\n")
        git(self.repo, "init", "-q")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")

    def tearDown(self):
        self.tmp.cleanup()

    def fix(self, test=GOOD_TEST, code=FIXED, name="test_total.py"):
        (self.repo / "calc.py").write_text(code)
        (self.repo / "tests" / name).write_text(test)

    def test_a_real_regression_test_is_red_then_green(self):
        self.fix()
        res = R.check(self.repo, CMD)
        self.assertEqual(res["verdict"], "red-green", res)
        self.assertEqual(res["tests"], ["tests/test_total.py"])

    def test_a_test_that_passes_without_the_fix_is_caught(self):
        self.fix(test=VACUOUS_TEST)
        self.assertEqual(R.check(self.repo, CMD)["verdict"], "not-red")

    def test_a_fix_that_doesnt_fix_is_caught(self):
        self.fix(code=BUGGY)
        self.assertEqual(R.check(self.repo, CMD)["verdict"], "not-green")

    def test_no_test_changes_means_nothing_to_prove(self):
        (self.repo / "calc.py").write_text(FIXED)
        self.assertEqual(R.check(self.repo, CMD)["verdict"], "no-tests")

    def test_expect_rejects_a_failure_for_the_wrong_reason(self):
        self.fix(test="import nonexistent_module\n")
        res = R.check(self.repo, CMD, expect=r"AssertionError")
        self.assertEqual(res["verdict"], "wrong-reason")

    def test_committed_fix_with_base_head_parent(self):
        self.fix()
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "fix")
        self.assertEqual(R.check(self.repo, CMD, base="HEAD~1")["verdict"], "red-green")

    def test_snapshot_pins_before_without_touching_the_index(self):
        (self.repo / "notes.txt").write_text("wip\n")          # uncommitted work that predates the fix
        snap = R.snapshot(self.repo)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "?? notes.txt")
        self.fix()
        res = R.check(self.repo, CMD, base=snap)
        self.assertEqual(res["verdict"], "red-green")
        self.assertIn("notes.txt", git(self.repo, "ls-tree", "-r", "--name-only", snap))

    def test_worktree_is_cleaned_up(self):
        self.fix()
        R.check(self.repo, CMD)
        self.assertEqual(len(git(self.repo, "worktree", "list").splitlines()), 1)

    def test_heavy_dirs_are_linked_into_the_before_tree(self):
        (self.repo / ".gitignore").write_text(".venv/\n")
        (self.repo / ".venv").mkdir()
        (self.repo / ".venv" / "helper.py").write_text("ANSWER = 1\n")
        self.fix(test="import sys; sys.path.insert(0, '.venv')\nimport helper\n" + GOOD_TEST)
        self.assertEqual(R.check(self.repo, CMD)["verdict"], "red-green")

    def test_test_path_shapes(self):
        for p in ["tests/a.py", "src/__tests__/a.js", "pkg/a_test.go", "src/a.spec.ts", "src/FooTest.java",
                  "test_a.py", "spec/models/a_spec.rb", "src/FooTests.cs"]:
            self.assertTrue(R.TEST_RE.search(p), p)
        for p in ["src/contest.py", "src/attestation.go", "README.md", "src/testimony/x.py"]:
            self.assertFalse(R.TEST_RE.search(p), p)


if __name__ == "__main__":
    unittest.main()
