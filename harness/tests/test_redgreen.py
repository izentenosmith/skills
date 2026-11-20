"""redgreen.py against throwaway git repos. Run: python3 -m unittest discover harness/tests"""
import contextlib
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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
        res = R.check(self.repo, CMD, shell=True)
        self.assertEqual(res["verdict"], "red-green", res)
        self.assertEqual(res["tests"], ["tests/test_total.py"])

    def test_a_test_that_passes_without_the_fix_is_caught(self):
        self.fix(test=VACUOUS_TEST)
        self.assertEqual(R.check(self.repo, CMD, shell=True)["verdict"], "not-red")

    def test_a_fix_that_doesnt_fix_is_caught(self):
        self.fix(code=BUGGY)
        self.assertEqual(R.check(self.repo, CMD, shell=True)["verdict"], "not-green")

    def test_no_test_changes_means_nothing_to_prove(self):
        (self.repo / "calc.py").write_text(FIXED)
        self.assertEqual(R.check(self.repo, CMD, shell=True)["verdict"], "no-tests")

    def test_expect_rejects_a_failure_for_the_wrong_reason(self):
        self.fix(test="import nonexistent_module\n")
        res = R.check(self.repo, CMD, shell=True, expect=r"AssertionError")
        self.assertEqual(res["verdict"], "wrong-reason")

    def test_a_test_that_imports_what_the_fix_adds_is_not_red_for_the_behavior(self):
        # The behavior was never broken; the before-run fails only because `add_all` doesn't exist yet.
        self.fix(code=BUGGY + "add_all = total\n", test="from calc import add_all\nassert add_all([1, 2]) == 3\n")
        res = R.check(self.repo, CMD, shell=True)
        self.assertEqual(res["verdict"], "wrong-reason", res)
        self.assertIn("cannot import name", res["load_errors"][0])

    def test_a_module_the_fix_adds_is_not_red_for_the_behavior(self):
        (self.repo / "fmt.py").write_text("def money(x):\n    return f'{x:.2f}'\n")
        self.fix(code=FIXED, test="from fmt import money\nassert money(1) == '1.00'\n")
        self.assertEqual(R.check(self.repo, CMD, shell=True)["verdict"], "wrong-reason")

    def test_a_real_red_still_counts_when_it_also_uses_a_new_symbol_from_an_existing_module(self):
        # `calc.total` exists before the fix, so the before-run executes the assertion and fails on it.
        self.fix(test="import calc\nassert calc.total([0.4, 0.4, 0.4]) == 1\n")
        self.assertEqual(R.check(self.repo, CMD, shell=True)["verdict"], "red-green")

    def test_load_error_noise_printed_by_both_runs_does_not_block_red(self):
        noisy = 'echo "warning: optional ImportError: no module named speedups"; ' + CMD
        self.fix()
        self.assertEqual(R.check(self.repo, noisy, shell=True)["verdict"], "red-green")

    def test_expect_decides_when_given(self):
        # An import error that *is* the bug: the caller says so, and the heuristic steps aside.
        self.fix(code=BUGGY + "add_all = total\n", test="from calc import add_all\n")
        self.assertEqual(R.check(self.repo, CMD, shell=True, expect=r"cannot import name")["verdict"], "red-green")

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_node_cannot_find_module_is_wrong_reason(self):
        (self.repo / "slug.js").write_text("module.exports = s => s.toLowerCase();\n")
        (self.repo / "tests" / "slug.test.js").write_text(
            "const assert = require('assert');\nassert.strictEqual(require('../slug')('A'), 'a');\n")
        res = R.check(self.repo, "node tests/slug.test.js")
        self.assertEqual(res["verdict"], "wrong-reason", res)
        self.assertIn("Cannot find module", " ".join(res["load_errors"]))

    @unittest.skipUnless(shutil.which("javac") and shutil.which("java"), "no JDK")
    def test_javac_cannot_find_symbol_is_wrong_reason(self):
        (self.repo / "Calc.java").write_text("class Calc { static int add(int a, int b) { return a + b; } }\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "java")
        (self.repo / "Calc.java").write_text("class Calc { static int add(int a, int b) { return a + b; }\n"
                                             "  static int twice(int a) { return add(a, a); } }\n")
        (self.repo / "CalcTest.java").write_text(
            "class CalcTest { public static void main(String[] a) {\n"
            "  if (Calc.twice(2) != 4) throw new AssertionError(); } }\n")
        cmd = "d=$(mktemp -d) && javac -d $d Calc.java CalcTest.java && java -cp $d CalcTest"
        res = R.check(self.repo, cmd, shell=True)
        self.assertEqual(res["verdict"], "wrong-reason", res)
        self.assertIn("cannot find symbol", " ".join(res["load_errors"]))

    def test_load_error_shapes_across_ecosystems(self):
        def verdict(out, code=1):
            return R.load_errors({"code": code, "output": out}, {"code": 0, "output": ""},
                                 pathlib.Path("/nowhere"), pathlib.Path("/repo"))
        loads = [
            "E   ModuleNotFoundError: No module named 'fmt'",
            "ERROR tests/test_x.py - ImportError: cannot import name 'add_all' from 'calc'",
            "==== 1 error in 0.05s ====\n_ ERROR collecting tests/test_x.py _",
            "AttributeError: module 'calc' has no attribute 'add_all'",
            "CalcTest.java:2: error: cannot find symbol",
            "[ERROR] COMPILATION ERROR :",
            "> Task :compileTestJava FAILED",
            "e: CalcTest.kt: (3, 9): Unresolved reference: twice",
            "Error: Cannot find module '../slug'",
            "SyntaxError: The requested module './a.js' does not provide an export named 'twice'",
            "src/a.test.ts(3,10): error TS2305: Module '\"./a\"' has no exported member 'twice'.",
            "  ● Test suite failed to run",
            "./calc_test.go:9:9: undefined: Twice\nFAIL\texample/calc [build failed]",
            "error[E0425]: cannot find function `twice` in this scope",
            "CalcTests.cs(9,20): error CS0117: 'Calc' does not contain a definition for 'Twice'",
            "LoadError: cannot load such file -- ./slug",
            "NameError: uninitialized constant Slug",
        ]
        for out in loads:
            self.assertTrue(verdict(out), out)
        pytest_out = "============ test session starts ============\ncollected 0 items\n\nInterrupted: 1 error"
        self.assertIn("pytest exit 2: the tests were not run", verdict(pytest_out, code=2))
        runs = [
            "AssertionError: 1 != 2",
            "FAILED tests/test_total.py::test_rounding - assert 2 == 1",
            "SyntaxError: Unexpected token } in JSON at position 12",          # JSON.parse — runtime
            "TypeError: callback is not a function",
            "expected: <4> but was: <3>",
            "--- FAIL: TestTwice (0.00s)",
        ]
        for out in runs:
            self.assertEqual(verdict(out), [], out)
        self.assertEqual(verdict("exit status 2"), [], "a bare exit 2 isn't pytest's")

    def test_committed_fix_with_base_head_parent(self):
        self.fix()
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "fix")
        self.assertEqual(R.check(self.repo, CMD, shell=True, base="HEAD~1")["verdict"], "red-green")

    def test_snapshot_pins_before_without_touching_the_index(self):
        (self.repo / "notes.txt").write_text("wip\n")          # uncommitted work that predates the fix
        snap = R.snapshot(self.repo)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "?? notes.txt")
        self.fix()
        res = R.check(self.repo, CMD, shell=True, base=snap)
        self.assertEqual(res["verdict"], "red-green")
        self.assertIn("notes.txt", git(self.repo, "ls-tree", "-r", "--name-only", snap))

    def test_snapshot_needs_no_git_identity(self):
        # A fresh CI runner or container has no user.name/user.email, and Linux git
        # won't guess one. The snapshot is an internal dangling commit, so it carries
        # its own identity instead of failing with "Author identity unknown".
        (self.repo / "notes.txt").write_text("wip\n")
        no_identity = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_COUNT": "1",
                       "GIT_CONFIG_KEY_0": "user.useConfigOnly", "GIT_CONFIG_VALUE_0": "true"}
        with mock.patch.dict(os.environ, no_identity):
            snap = R.snapshot(self.repo)
        self.assertIn("notes.txt", git(self.repo, "ls-tree", "-r", "--name-only", snap))

    def test_worktree_is_cleaned_up(self):
        self.fix()
        R.check(self.repo, CMD, shell=True)
        self.assertEqual(len(git(self.repo, "worktree", "list").splitlines()), 1)

    def test_heavy_dirs_are_linked_into_the_before_tree(self):
        (self.repo / ".gitignore").write_text(".venv/\n")
        (self.repo / ".venv").mkdir()
        (self.repo / ".venv" / "helper.py").write_text("ANSWER = 1\n")
        self.fix(test="import sys; sys.path.insert(0, '.venv')\nimport helper\n" + GOOD_TEST)
        self.assertEqual(R.check(self.repo, CMD, shell=True)["verdict"], "red-green")

    # --- the command runs without a shell unless a person says otherwise

    PLAIN = "python3 tests/test_total.py"

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = R.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_a_plain_command_runs_without_a_shell(self):
        self.fix(test="import sys; sys.path.insert(0, '.')\n" + GOOD_TEST)
        with mock.patch.object(R.subprocess, "run", wraps=subprocess.run) as spy:
            res = R.check(self.repo, self.PLAIN)
        self.assertEqual(res["verdict"], "red-green", res)
        self.assertFalse(any(c.kwargs.get("shell") for c in spy.call_args_list))

    def test_leading_assignments_become_environment_without_a_shell(self):
        self.fix()                                  # GOOD_TEST imports calc: it needs PYTHONPATH=.
        res = R.check(self.repo, "PYTHONPATH=. MARK='a b' " + self.PLAIN)
        self.assertEqual(res["verdict"], "red-green", res)
        self.assertEqual(R.argv_for("A=1 B='x y' pytest -q {tests}", ["t/a b.py"]),
                         (["pytest", "-q", "t/a b.py"], {"A": "1", "B": "x y"}))

    def test_a_command_that_needs_a_shell_is_refused_by_default(self):
        self.fix()
        for cmd in ("pytest; touch pwned", "pytest | tee log", "a && b", "pytest > out", "pytest < in",
                    "echo `id`", "echo $(id)", "echo $HOME", "echo ${HOME}", "pytest\ntouch pwned"):
            with self.subTest(cmd=cmd), self.assertRaises(R.Usage):
                R.check(self.repo, cmd)
        self.assertFalse((self.repo / "pwned").exists())
        self.assertEqual(len(git(self.repo, "worktree", "list").splitlines()), 1)

    def test_cli_refuses_a_shell_command_with_status_2_and_runs_it_with_the_flag(self):
        self.fix()
        code, _, err = self.cli("check", "--repo", str(self.repo), "--cmd", CMD)
        self.assertEqual(code, 2)
        self.assertIn("needs a shell", err)
        self.assertIn("--shell", err)
        code, out, _ = self.cli("check", "--repo", str(self.repo), "--cmd", CMD, "--shell")
        self.assertEqual(code, 0, out)
        self.assertIn("red-green", out)

    def test_a_program_that_does_not_exist_is_a_failed_run_not_a_crash(self):
        self.fix()
        res = R.check(self.repo, "no-such-program-xyz tests/test_total.py")
        self.assertEqual(res["verdict"], "not-green", res)
        self.assertEqual(res["after"]["code"], 127)

    # --- a wrong path is a usage error, not a quiet result

    def test_a_repo_that_does_not_exist_is_status_2(self):
        for sub in (("check", "--cmd", self.PLAIN), ("snapshot",)):
            code, _, err = self.cli(*sub, "--repo", str(self.repo / "nope"))
            self.assertEqual(code, 2, sub)
            self.assertIn("no such directory", err)

    def test_a_tests_path_that_exists_nowhere_is_status_2(self):
        self.fix()
        code, _, err = self.cli("check", "--repo", str(self.repo), "--cmd", self.PLAIN, "--tests", "tests/nope.py")
        self.assertEqual(code, 2)
        self.assertIn("no such test file", err)

    def test_a_tests_path_deleted_since_the_base_is_still_accepted(self):
        (self.repo / "tests" / "test_existing.py").unlink()
        res = R.check(self.repo, self.PLAIN, tests=["tests/test_existing.py"])
        self.assertEqual((res["verdict"], res["deleted_tests"]), ("no-tests", ["tests/test_existing.py"]))

    def test_test_path_shapes(self):
        for p in ["tests/a.py", "src/__tests__/a.js", "pkg/a_test.go", "src/a.spec.ts", "src/FooTest.java",
                  "test_a.py", "spec/models/a_spec.rb", "src/FooTests.cs"]:
            self.assertTrue(R.TEST_RE.search(p), p)
        for p in ["src/contest.py", "src/attestation.go", "README.md", "src/testimony/x.py"]:
            self.assertFalse(R.TEST_RE.search(p), p)


if __name__ == "__main__":
    unittest.main()
