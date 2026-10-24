"""netreview.py: redaction, the gate, scoring with harness findings, and the whole run against fake_claude.
Run: python3 -m unittest discover harness/tests"""
import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile
import types
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import netreview as NR  # noqa: E402

FAKE = HERE / "fake_claude.py"
IOS = """hostname edge-1
enable secret 5 $1$abcd$SuperSecretHash
username admin privilege 15 password 7 0822455D0A16
snmp-server community public RO
crypto isakmp key MyPSK-123 address 203.0.113.9
interface Gi0/0
 ip address 10.10.10.1 255.255.255.0
line vty 0 4
 transport input telnet
"""
TF = """resource "azurerm_virtual_network_gateway_connection" "s2s" {
  shared_key = "hunter2-very-secret"
  other      = var.not_secret
  admin_password = "${var.admin_password}"
}
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA
-----END RSA PRIVATE KEY-----
"""
SECRETS = ("SuperSecretHash", "0822455D0A16", "MyPSK-123", "hunter2-very-secret", "MIIEowIBAAKCAQEA")


class Redaction(unittest.TestCase):
    def test_values_are_masked_and_lines_kept(self):
        for text in (IOS, TF):
            masked, findings = NR.redact(text, "x.conf")
            self.assertEqual(masked.count("\n"), text.count("\n"))
            for s in SECRETS:
                self.assertNotIn(s, masked)
                self.assertFalse(any(s in json.dumps(f) for f in findings), s)
            self.assertTrue(findings)

    def test_default_and_weak_secrets_are_named(self):
        _, findings = NR.redact(IOS, "edge-1.conf")
        text = " ".join(f["summary"] for f in findings)
        self.assertIn("default value", text)                     # snmp community public
        self.assertIn("reversible encoding", text)               # type 7
        self.assertTrue(all(f["evidence"].startswith("edge-1.conf:") for f in findings))
        self.assertIn("edge-1.conf:4", {f["evidence"] for f in findings})

    def test_variables_are_not_secrets(self):
        masked, _ = NR.redact(TF, "main.tf")
        self.assertIn("var.not_secret", masked)
        self.assertIn("${var.admin_password}", masked)


def crit(in_scope, satisfied):
    return {"rubric": "segmentation", "criterion": "c", "in_scope": in_scope, "satisfied": satisfied, "proxy_only": False}


class Scoring(unittest.TestCase):
    def result(self, criteria, findings=()):
        return {"usage_status": "in-use", "domains": [{"domain": "segmentation", "coverage": "all", "objects": 10,
                                                       "evaluation_md": "", "criteria": criteria,
                                                       "findings": list(findings)}]}

    def test_harness_findings_cap_the_network(self):
        spof = {"id": "NG-SPOF-fw-a", "object": "fw-a", "severity": "High", "confidence": "decidable",
                "theory": "graph-theory G4", "evidence": "main.tf:10", "summary": "single firewall"}
        d = NR.score_network(self.result([crit(10, 10)]), [spof], [], {"resilience": 3})
        self.assertEqual(d["score"], 6.0)
        self.assertEqual(d["high"], 1)
        self.assertIn("resilience", [x["domain"] for x in d["domains"]])

    def test_secret_findings_land_in_security(self):
        _, secrets = NR.redact(IOS, "edge-1.conf")
        d = NR.score_network(self.result([crit(10, 10)]), [], secrets, {})
        self.assertIn("security", [x["domain"] for x in d["domains"]])

    def test_domain_routing_of_harness_findings(self):
        self.assertEqual(NR.domain_of({"id": "NG-OVERLAP-a-b", "theory": "theory §3"}), "addressing")
        self.assertEqual(NR.domain_of({"id": "NG-MGMT-f1", "theory": "theory §12"}), "segmentation")
        self.assertEqual(NR.domain_of({"id": "NG-BRIDGE-e1", "theory": "graph-theory G4"}), "resilience")


class Gate(unittest.TestCase):
    a = types.SimpleNamespace(intent="remediation", good_enough=9.0, max_flag_ratio=0.10, min_connectivity=2)
    good = {"score": 9.5, "critical": 0, "high": 0, "usage": "in-use", "flags": 0, "objects": 40,
            "critical_pairs": [{"from": "internet", "to": "snet-app", "node_connectivity": 2}]}

    def test_good_enough_skips(self):
        self.assertTrue(NR.gate("x", self.good, self.a)[0])

    def test_each_reason_to_propose(self):
        for change in ({"score": 8.9}, {"high": 1}, {"usage": "duplicate"}, {"flags": 5}, {"critical_pairs": []},
                       {"critical_pairs": None},
                       {"critical_pairs": [{"from": "a", "to": "b", "node_connectivity": 1}]}):
            self.assertFalse(NR.gate("x", {**self.good, **change}, self.a)[0], change)

    def test_migration_always_proposes(self):
        self.assertFalse(NR.gate("x", self.good, types.SimpleNamespace(**{**vars(self.a), "intent": "migration"}))[0])


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        for net in ("prod", "legacy"):
            (self.root / "ev" / net).mkdir(parents=True)
            (self.root / "ev" / net / "main.tf").write_text(TF)
            (self.root / "ev" / net / "edge-1.conf").write_text(IOS)
        self.out = self.root / "review"

    def tearDown(self):
        self.tmp.cleanup()

    def run_net(self, variant="good", *extra, nets=("prod", "legacy")):
        env = {"HARNESS_CLAUDE": str(FAKE), "FAKE_NET": variant, "FAKE_CLAUDE_LOG": str(self.root / "calls.jsonl")}
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        buf = io.StringIO()
        args = ["--out", str(self.out), *extra]
        for n in nets:
            args += ["--evidence", f"{n}={self.root / 'ev' / n}"]
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                code = NR.main(args)
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.output = buf.getvalue()
        return code

    def calls(self):
        log = self.root / "calls.jsonl"
        return [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []

    def test_no_secret_reaches_a_prompt_or_an_output(self):
        self.run_net("good", "--audit-only")
        texts = [p.read_text(errors="replace") for p in (self.out / "runs").rglob("*.prompt.md")]
        texts += [p.read_text(errors="replace") for p in self.out.rglob("*") if p.is_file() and p.suffix in (".md", ".json", ".tf", ".conf")]
        self.assertTrue(texts)
        for t in texts:
            for s in SECRETS:
                self.assertNotIn(s, t)
        audits = [c for c in self.calls() if c["stage"] == "net-audit"]
        self.assertEqual(len(audits), 2)
        for c in audits:
            self.assertIn(str(self.out / "evidence"), c["cwd"])      # audit agents work inside the redacted copy

    def test_secrets_cap_the_score_and_force_a_proposal(self):
        self.assertEqual(self.run_net("good"), NR.EXIT_OK, self.output)
        scores = json.loads((self.out / "audit/scores.json").read_text())["networks"]
        self.assertEqual(scores["prod"]["cap"], 6.0)          # committed secrets are High
        self.assertIn("net-propose", [c["stage"] for c in self.calls()])

    def test_a_clean_network_passes_the_gate(self):
        for net in ("prod", "legacy"):
            (self.root / "ev" / net / "edge-1.conf").write_text("hostname edge-1\n")
            (self.root / "ev" / net / "main.tf").write_text('resource "azurerm_virtual_network" "hub" {}\n')
        self.assertEqual(self.run_net("good"), NR.EXIT_OK, self.output)
        self.assertNotIn("net-propose", [c["stage"] for c in self.calls()])
        self.assertIn("**no** — good enough", (self.out / "gate.md").read_text())
        summary = (self.out / "audit/prod/summary.md").read_text()
        self.assertIn("internet → snet-app | 2", summary)
        self.assertTrue((self.out / "audit/prod/topology.json").exists())
        self.assertIn("legacy → prod via peering", (self.out / "audit/estate-analysis.md").read_text())

    def test_a_single_firewall_fails_the_connectivity_gate(self):
        for net in ("prod", "legacy"):
            (self.root / "ev" / net / "edge-1.conf").write_text("hostname edge-1\n")
            (self.root / "ev" / net / "main.tf").write_text("\n")
        self.assertEqual(self.run_net("spof", "--audit-only"), NR.EXIT_OK, self.output)
        gate = (self.out / "gate.md").read_text()
        self.assertIn("below node connectivity 2", gate)
        self.assertIn("fw-a", (self.out / "audit/prod/resilience.md").read_text())

    def test_no_critical_pairs_is_unassessed(self):
        self.run_net("nopairs", "--audit-only")
        self.assertIn("no critical pairs declared", (self.out / "gate.md").read_text())

    def test_unparseable_topology_is_an_error_after_one_retry(self):
        self.assertEqual(self.run_net("badtopo", "--audit-only", nets=("prod",)), NR.EXIT_ERROR)
        self.assertEqual([c["stage"] for c in self.calls()].count("net-audit"), 2)

    def test_missing_evidence_is_a_usage_error(self):
        self.assertEqual(self.run_net("good", nets=()), NR.EXIT_USAGE)


if __name__ == "__main__":
    unittest.main()
