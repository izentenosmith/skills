"""dbreview.py: the scoring formula, the gate, read-only acquisition, and the whole run against fake_claude.
Run: python3 -m unittest discover harness/tests"""
import contextlib
import hashlib
import io
import json
import os
import pathlib
import sqlite3
import sys
import tempfile
import types
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import dbreview as DB  # noqa: E402

FAKE = HERE / "fake_claude.py"
TABLES = "CREATE TABLE orders (id int PRIMARY KEY);\nCREATE INDEX ix ON orders(id);\nCREATE VIEW v AS SELECT 1;\n"


def crit(in_scope, satisfied, proxy=False):
    return {"rubric": "tables", "criterion": "c", "in_scope": in_scope, "satisfied": satisfied, "proxy_only": proxy}


def finding(sev, conf="decidable"):
    return {"id": "X", "object": "o", "severity": sev, "confidence": conf, "theory": "t", "evidence": "e", "summary": "s"}


class Scoring(unittest.TestCase):
    def test_proportional_points(self):
        self.assertEqual(DB.criterion_points(crit(100, 95))[1], 2)
        self.assertEqual(DB.criterion_points(crit(100, 94))[1], 1)
        self.assertEqual(DB.criterion_points(crit(100, 50))[1], 1)
        self.assertEqual(DB.criterion_points(crit(100, 49))[1], 0)
        self.assertEqual(DB.criterion_points(crit(0, 0)), (None, None))      # not in scope: not graded

    def test_proxy_alone_never_grades_red(self):
        self.assertEqual(DB.criterion_points(crit(10, 1, proxy=True))[1], 1)

    def test_base_and_caps(self):
        f = {"criteria": [crit(10, 10), crit(10, 7)], "findings": []}
        self.assertEqual(DB.score_file(f)["score"], 7.5)               # (2 + 1) / 4 × 10
        f["findings"] = [finding("High")]
        self.assertEqual(DB.score_file(f)["score"], 6.0)
        f["findings"] = [finding("Critical"), finding("High")]
        self.assertEqual(DB.score_file(f)["score"], 2.0)

    def test_a_binding_cap_is_named_as_such(self):
        by = finding("High")
        self.assertTrue(DB.cap_text(6.0, by, 8.0).startswith("capped at 6.0"))
        self.assertIn("not binding", DB.cap_text(6.0, by, 4.0))

    def test_needs_data_never_moves_a_score(self):
        f = {"criteria": [crit(10, 10)], "findings": [finding("Critical", "needs-data")]}
        self.assertEqual(DB.score_file(f)["score"], 10.0)

    def test_bands(self):
        self.assertEqual(DB.band(9.0), "Exemplary")
        self.assertEqual(DB.band(8.9), "Good, minor debt")
        self.assertEqual(DB.band(2.9), "Critical / unsafe")


class Gate(unittest.TestCase):
    a = types.SimpleNamespace(intent="remediation", good_enough=9.0, max_flag_ratio=0.10)
    good = {"score": 9.5, "critical": 0, "high": 0, "usage": "used", "flags": 1, "objects": 40}

    def test_good_enough_skips(self):
        self.assertTrue(DB.gate("x", self.good, self.a)[0])

    def test_each_reason_to_propose(self):
        for change in ({"score": 8.9}, {"high": 1}, {"usage": "copy"}, {"flags": 5}):
            self.assertFalse(DB.gate("x", {**self.good, **change}, self.a)[0], change)

    def test_migration_always_proposes(self):
        self.assertFalse(DB.gate("x", self.good, types.SimpleNamespace(**{**vars(self.a), "intent": "migration"}))[0])


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        for db in ("sales", "legacy"):
            (self.root / "ddl" / db).mkdir(parents=True)
            (self.root / "ddl" / db / "tables.sql").write_text(TABLES)
        self.out = self.root / "review"

    def tearDown(self):
        self.tmp.cleanup()

    def run_db(self, variant="good", *extra, ddl=True, env=None):
        env = {"HARNESS_CLAUDE": str(FAKE), "FAKE_DB": variant, "FAKE_CLAUDE_LOG": str(self.root / "calls.jsonl"),
               **(env or {})}
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        buf = io.StringIO()
        args = ["--out", str(self.out), *extra]
        if ddl:
            args += ["--ddl", f"sales={self.root / 'ddl/sales'}", "--ddl", f"legacy={self.root / 'ddl/legacy'}"]
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                code = DB.main(args)
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.output = buf.getvalue()
        return code

    def stages(self):
        log = self.root / "calls.jsonl"
        return [json.loads(l)["stage"] for l in log.read_text().splitlines()] if log.exists() else []

    def test_a_good_estate_gets_no_proposal(self):
        self.assertEqual(self.run_db("good"), DB.EXIT_OK, self.output)
        self.assertNotIn("db-propose", self.stages())
        self.assertIn("**no** — good enough", (self.out / "gate.md").read_text())
        self.assertFalse((self.out / "proposal").exists())
        self.assertIn("File score: 10.0", (self.out / "audit/sales/tables-evaluation.md").read_text())

    def test_only_the_weak_database_is_proposed(self):
        self.assertEqual(self.run_db("mixed"), DB.EXIT_OK, self.output)
        register = (self.out / "proposal/reuse-rework-register.md").read_text()
        self.assertIn("Proposed for: legacy", register)
        self.assertNotIn("sales", register)
        scores = json.loads((self.out / "audit/scores.json").read_text())["databases"]
        self.assertEqual(scores["legacy"]["score"], 2.5)               # 🔴 0 + 🟡 1 of 4 points; under the High cap
        self.assertIn("cap 6.0 from High T-1 — not binding", (self.out / "audit/legacy/summary.md").read_text())
        self.assertIn("legacy → sales", (self.out / "audit/estate-analysis.md").read_text())

    def test_flags_and_dead_schemas_are_proposed(self):
        for variant in ("flags", "dead"):
            self.assertEqual(self.run_db(variant), DB.EXIT_OK, self.output)
            self.assertIn("db-propose", self.stages(), variant)
            (self.root / "calls.jsonl").unlink()

    def test_migration_intent_proposes_everything(self):
        self.run_db("good", "--intent", "migration")
        register = (self.out / "proposal/reuse-rework-register.md").read_text()
        self.assertIn("sales", register)
        self.assertIn("legacy", register)

    def test_audit_only_stops_at_the_gate(self):
        self.run_db("mixed", "--audit-only")
        self.assertNotIn("db-propose", self.stages())
        self.assertTrue((self.out / "gate.md").exists())

    def test_a_connection_is_dumped_read_only_and_never_logged(self):
        path = self.root / "shop.db"
        con = sqlite3.connect(path)
        con.executescript("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);"
                          "CREATE INDEX ix_name ON customers(name);")
        con.close()
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        dsn = f"sqlite:///{path}"
        self.assertEqual(self.run_db("good", "--dsn-env", "SHOP_DSN", ddl=False, env={"SHOP_DSN": dsn}),
                         DB.EXIT_OK, self.output)
        self.assertIn("CREATE TABLE customers", (self.out / "ddl/shop.sql").read_text())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
        self.assertNotIn(dsn, self.output)
        for f in self.out.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".json", ".sql", ".txt"):
                self.assertNotIn(dsn, f.read_text(errors="replace"), f)

    def test_unsupported_and_missing_connections_are_usage_errors(self):
        self.assertEqual(self.run_db("good", "--dsn-env", "X", ddl=False, env={"X": "sqlserver://u:p@h/db"}),
                         DB.EXIT_USAGE)
        self.assertIn("export the DDL", self.output)
        self.assertEqual(self.run_db("good", "--dsn-env", "EMPTY_VAR_FOR_TEST", ddl=False), DB.EXIT_USAGE)

    def test_inventory_counts_objects(self):
        self.run_db("good")
        inv = json.loads((self.out / "inventory.json").read_text())
        self.assertEqual(inv["sales"], {"tables": 1, "indexes": 1, "views": 1, "procedures": 0, "triggers": 0})


if __name__ == "__main__":
    unittest.main()
