"""networkflow.py: stage rules, the canonical diagram checks, and new-network runs against fake_claude.
Run: python3 -m unittest discover harness/tests"""
import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import networkflow as NF  # noqa: E402

FAKE = HERE / "fake_claude.py"
TOPO = {"meta": {"name": "t", "source_version": "x", "rubric": "v1.0", "stage": "design", "status": "proposed"},
        "nodes": [{"id": "internet", "kind": "internet", "zone": "internet", "site": "g", "attrs": {}, "evidence": "a:1"},
                  {"id": "vnet-hub", "kind": "vnet", "zone": "app", "site": "r", "attrs": {}, "evidence": "a:2"}],
        "edges": [{"id": "e1", "a": "internet", "b": "vnet-hub", "kind": "l3-adjacency", "redundancy_group": None,
                   "attrs": {}, "evidence": "a:3"}],
        "networks": [{"id": "vnet-hub", "cidr": "10.0.0.0/16", "parent": None, "purpose": "hub", "evidence": "a:2"}],
        "zones": [{"id": "internet", "trust": 0, "purpose": "u"}, {"id": "app", "trust": 2, "purpose": "a"}],
        "flows": [], "critical_pairs": [{"from": "internet", "to": "vnet-hub", "why": "x"}]}


def page(name, cells, legend=True):
    leg = '<mxCell id="deco-legend" value="Network diagram conventions" vertex="1" parent="1"/>' if legend else ""
    return (f'<mxfile><diagram name="{name}"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            f'{leg}{cells}</root></mxGraphModel></diagram></mxfile>')


LOGICAL = ('<mxCell id="internet" value="internet" vertex="1" parent="1"/>'
           '<mxCell id="vnet-hub" value="vnet-hub&lt;br&gt;10.0.0.0/16" vertex="1" parent="1"/>'
           '<mxCell id="e1" edge="1" source="internet" target="vnet-hub" parent="1"/>')
SEG = ('<mxCell id="internet" value="internet — trust 0" vertex="1" parent="1"/>'
       '<mxCell id="app" value="app — trust 2" vertex="1" parent="1"/>')


class Diagrams(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, logical=None, seg=None):
        lp, sp = self.dir / "logical-topology.drawio", self.dir / "segmentation.drawio"
        lp.write_text(logical or page("Logical topology (L3)", LOGICAL))
        sp.write_text(seg or page("Segmentation (zones and flows)", SEG))
        return [lp, sp]

    def test_a_conforming_pair_passes(self):
        self.assertEqual(len(NF.validate_diagram_set(self.write(), TOPO)), 2)

    def test_rejections(self):
        cases = {
            "page named": dict(logical=page("Page-1", LOGICAL)),
            "legend": dict(logical=page("Logical topology (L3)", LOGICAL, legend=False)),
            "CIDR": dict(logical=page("Logical topology (L3)", LOGICAL.replace("10.0.0.0/16", "10.9.0.0/16"))),
            "not a topology.json id": dict(logical=page("Logical topology (L3)", LOGICAL + '<mxCell id="stray" vertex="1" parent="1"/>')),
            "zone 'app'": dict(seg=page("Segmentation (zones and flows)", SEG.split("<mxCell id=\"app\"")[0])),
            "invalid draw.io XML": dict(logical="<mxfile><diagram"),
        }
        for needle, kw in cases.items():
            with self.assertRaises(NF.loop.HarnessError, msg=needle) as cm:
                NF.validate_diagram_set(self.write(**kw), TOPO)
            self.assertIn(needle, str(cm.exception))

    def test_missing_view_and_l2_needs_physical(self):
        paths = self.write()
        with self.assertRaises(NF.loop.HarnessError):
            NF.validate_diagram_set(paths[:1], TOPO)
        l2 = {**TOPO, "edges": [{**TOPO["edges"][0], "kind": "l2-link"}]}
        with self.assertRaisesRegex(NF.loop.HarnessError, "physical-topology"):
            NF.validate_diagram_set(paths, l2)

    def test_without_a_model_only_structure_is_checked(self):
        self.assertEqual(len(NF.validate_diagram_set(self.write(logical=page("Logical topology (L3)", '<mxCell id="x" vertex="1" parent="1"/>')))), 2)


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "req.md").write_text("# Requirements\n\nA storefront behind redundant firewalls.\n")
        self.out = self.root / "work"

    def tearDown(self):
        self.tmp.cleanup()

    def run_nf(self, *args, variant="ok"):
        env = {"HARNESS_CLAUDE": str(FAKE), "FAKE_NF": variant, "FAKE_CLAUDE_LOG": str(self.root / "calls.jsonl")}
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                code = NF.main(["--out", str(self.out), *args])
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.output = buf.getvalue()
        return code

    def stages(self):
        log = self.root / "calls.jsonl"
        return [json.loads(l)["stage"] for l in log.read_text().splitlines()] if log.exists() else []

    def test_new_network_design_diagram_propose(self):
        self.assertEqual(self.run_nf("--mode", "new", "--requirements", str(self.root / "req.md")), NF.EXIT_OK, self.output)
        self.assertEqual(self.stages(), ["nf-design", "nf-diagram", "nf-propose"])
        for p in ("design/design.md", "design/topology.json", "design/graph.json", "diagrams/logical-topology.drawio",
                  "diagrams/segmentation.drawio", "proposal/proposal.md"):
            self.assertTrue((self.out / p).exists(), p)
        self.assertNotIn("nf-blueprint", self.stages())

    def test_bad_diagrams_stop_before_the_proposal(self):
        for variant in ("badcidr", "nolegend"):
            self.assertEqual(self.run_nf("--mode", "new", "--requirements", str(self.root / "req.md"), variant=variant),
                             NF.EXIT_ERROR, variant)
            self.assertNotIn("nf-propose", self.stages())
            (self.root / "calls.jsonl").unlink()

    def test_blueprint_needs_explicit_acceptance_and_its_own_run(self):
        self.assertEqual(self.run_nf("--mode", "new", "--stages", "blueprint", "--proposal-input", "p.md",
                                     "--design-input", "d"), NF.EXIT_USAGE)
        self.assertIn("--proposal-accepted", self.output)
        self.assertEqual(self.run_nf("--mode", "new", "--stages", "propose,blueprint"), NF.EXIT_USAGE)
        self.assertEqual(self.stages(), [])

    def test_accepted_proposal_produces_the_package(self):
        self.run_nf("--mode", "new", "--requirements", str(self.root / "req.md"))
        code = self.run_nf("--mode", "new", "--stages", "blueprint", "--proposal-accepted",
                           "--proposal-input", str(self.out / "proposal/proposal.md"), "--design-input", str(self.out / "design"))
        self.assertEqual(code, NF.EXIT_OK, self.output)
        final = json.loads((self.out / "blueprint/topology.json").read_text())
        self.assertEqual(final["meta"]["status"], "accepted")
        for p in ("network-design.md", "logical-topology.drawio", "segmentation.drawio", "graph.json"):
            self.assertTrue((self.out / "blueprint" / p).exists(), p)
        self.assertFalse(list((self.out / "blueprint").glob("*.tf")))

    def test_stage_order_and_mode_rules(self):
        self.assertEqual(self.run_nf("--mode", "new", "--stages", "diagram,design"), NF.EXIT_USAGE)
        self.assertEqual(self.run_nf("--mode", "new", "--stages", "audit"), NF.EXIT_USAGE)
        self.assertEqual(self.run_nf("--mode", "existing"), NF.EXIT_USAGE)          # audit needs --evidence

    def test_dry_run_calls_nothing(self):
        self.assertEqual(self.run_nf("--mode", "new", "--requirements", str(self.root / "req.md"), "--dry-run"),
                         NF.EXIT_OK, self.output)
        self.assertEqual(self.stages(), [])
        prompts = list((self.out / "runs").rglob("*.prompt.md"))
        self.assertEqual(len(prompts), 3)


if __name__ == "__main__":
    unittest.main()
