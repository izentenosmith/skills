"""netgraph.py: the graph algorithms on hand-computed graphs, the address and flow checks, and the CLI.
Run: python3 -m unittest discover harness/tests"""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import netgraph as NG  # noqa: E402


def node(id, kind="router", evidence=None, **attrs):
    return {"id": id, "kind": kind, "zone": attrs.pop("zone", None), "site": "dc1", "attrs": attrs,
            "evidence": evidence or f"configs/{id}.cfg:1"}


def edge(id, a, b, kind="l2-link", evidence=None):
    return {"id": id, "a": a, "b": b, "kind": kind, "redundancy_group": None, "attrs": {},
            "evidence": evidence or f"configs/{a}.cfg:9"}


def flow(id, src, dst, ports, action="allow", priority=100, proto="tcp", evidence=None):
    return {"id": id, "from_zone": src, "to_zone": dst, "proto": proto, "ports": ports, "action": action,
            "priority": priority, "evidence": evidence or f"infra/nsg.tf:{priority}"}


def topo(nodes, edges, **rest):
    return {"meta": {"name": "t", "source_version": "git abc", "rubric": "v1.0", "stage": "audit",
                     "status": "recovered"}, "nodes": nodes, "edges": edges, **rest}


def graph(pairs):
    """[('a','b'), …] → (nodes, edges) with edge ids e0, e1, …"""
    nodes = list(dict.fromkeys(v for p in pairs for v in p))
    return nodes, [(f"e{i}", a, b) for i, (a, b) in enumerate(pairs)]


def ids(result, prefix=""):
    return [f["id"] for f in result["findings"] if f["id"].startswith(prefix)]


class Graphs(unittest.TestCase):
    def test_a_ring_has_no_articulation_points_or_bridges(self):
        nodes, edges = graph([("a", "b"), ("b", "c"), ("c", "d"), ("d", "e"), ("e", "a")])
        self.assertEqual(NG.cut_structure(nodes, edges), ([], []))

    def test_a_star_hub_is_the_only_articulation_point_and_every_spoke_a_bridge(self):
        nodes, edges = graph([("hub", s) for s in "abcd"])
        self.assertEqual(NG.cut_structure(nodes, edges), (["hub"], ["e0", "e1", "e2", "e3"]))

    def test_parallel_edges_are_not_bridges(self):
        nodes, edges = graph([("a", "b"), ("a", "b"), ("b", "c")])
        self.assertEqual(NG.cut_structure(nodes, edges), (["b"], ["e2"]))

    def test_a_path_graphs_betweenness_matches_the_known_values(self):
        # P5: v2 lies on 3 of the 6 pairs that exclude it, v3 on 4 of 6, the ends on none
        nodes, edges = graph([("v1", "v2"), ("v2", "v3"), ("v3", "v4"), ("v4", "v5")])
        bc = NG.betweenness(nodes, edges)
        for v, want in {"v1": 0, "v2": 3 / 6, "v3": 4 / 6, "v4": 3 / 6, "v5": 0}.items():
            self.assertAlmostEqual(bc[v], want, places=9, msg=v)

    def test_components_largest_first(self):
        nodes, edges = graph([("a", "b"), ("b", "c"), ("x", "y")])
        self.assertEqual(NG.components(nodes + ["z"], edges), [["a", "b", "c"], ["x", "y"], ["z"]])

    def test_menger_counts_on_two_disjoint_paths_equal_two(self):
        nodes, edges = graph([("s", "a"), ("a", "t"), ("s", "b"), ("b", "t")])
        self.assertEqual(NG.connectivity(nodes, edges, {"s"}, {"t"}), (2, 2))

    def test_a_shared_middle_node_cuts_node_but_not_edge_connectivity(self):
        # s=m=t: two edge-disjoint paths, both through m
        nodes, edges = graph([("s", "m"), ("s", "m"), ("m", "t"), ("m", "t")])
        self.assertEqual(NG.connectivity(nodes, edges, {"s"}, {"t"}), (1, 2))
        self.assertEqual(NG.separators(nodes, edges, {"s"}, {"t"}), (["m"], []))

    def test_hub_concentration_and_degree_distribution(self):
        nodes, edges = graph([("hub", s) for s in "abcdefghi"])
        m = NG.graph_metrics(nodes, edges, runs=2)
        self.assertEqual(m["degree"]["distribution"], {"1": 9, "9": 1})
        self.assertEqual(m["degree"]["hub_nodes"], ["hub"])
        self.assertEqual(m["hub_concentration"], 0.5)                  # 9 of 18 endpoints

    def test_a_minimum_cut_has_as_many_members_as_the_connectivity(self):
        nodes, edges = graph([("s", "a"), ("a", "t"), ("s", "b"), ("b", "t")])
        self.assertEqual(NG.min_cut(nodes, edges, {"s"}, {"t"}), ["a", "b"])
        nodes, edges = graph([("s", "m"), ("m", "t"), ("s", "t")])     # the direct edge has no node to cut
        self.assertEqual(NG.min_cut(nodes, edges, {"s"}, {"t"}), ["e2", "m"])
        self.assertEqual(NG.min_cut(["s", "t"], [], {"s"}, {"t"}), [])

    def test_targeted_attack_breaks_a_star_that_random_failure_barely_dents(self):
        nodes, edges = graph([("hub", s) for s in "abcdefghi"])
        rob = NG.robustness(nodes, edges, seed=7, runs=50)
        self.assertEqual(rob["degree"][0], 1.0)
        self.assertEqual(rob["degree"][2], 0.1)                        # 10% removed = the hub
        self.assertGreater(rob["random"][2], 0.5)
        self.assertEqual(rob, NG.robustness(nodes, edges, seed=7, runs=50))   # deterministic for a seed


def uplink(ha=False, shared_fate=False):
    """users → (r1 [and r2]) → internet, with users → internet as the critical pair."""
    routers = ["r1", "r2"] if ha else ["r1"]
    extra = {"shared_fate": "edge-pair"} if shared_fate else {}
    nodes = [node("users", "lan"), node("internet", "internet", zone="internet")]
    nodes += [node(r, **extra) for r in routers]
    edges = [e for r in routers for e in (edge(f"e-users-{r}", "users", r), edge(f"e-{r}-isp", r, "internet"))]
    return topo(nodes, edges, critical_pairs=[{"from": "users", "to": "internet", "why": "users reach the internet"}])


class Resilience(unittest.TestCase):
    def test_a_single_uplink_is_a_spof_and_its_links_are_bridges(self):
        r = NG.analyze(uplink())
        self.assertEqual(r["errors"], [])
        self.assertEqual(ids(r, "NG-SPOF"), ["NG-SPOF-r1"])
        self.assertEqual(ids(r, "NG-BRIDGE"), ["NG-BRIDGE-e-r1-isp", "NG-BRIDGE-e-users-r1"])
        spof = next(f for f in r["findings"] if f["id"] == "NG-SPOF-r1")
        self.assertEqual((spof["severity"], spof["confidence"], spof["theory"]), ("High", "decidable", "graph-theory G4"))
        self.assertEqual(r["metrics"]["critical_pairs"][0]["node_connectivity"], 1)

    def test_an_ha_pair_is_not_a_spof(self):
        r = NG.analyze(uplink(ha=True))
        self.assertEqual(ids(r, "NG-SPOF") + ids(r, "NG-BRIDGE"), [])
        self.assertEqual(r["metrics"]["critical_pairs"][0]["node_connectivity"], 2)

    def test_marking_the_ha_pair_shared_fate_brings_the_spof_back(self):
        r = NG.analyze(uplink(ha=True, shared_fate=True))
        self.assertEqual(ids(r, "NG-SPOF"), ["NG-SPOF-edge-pair"])
        self.assertEqual(ids(r, "NG-BRIDGE"), [])                      # each side still has two links
        pair = r["metrics"]["critical_pairs"][0]
        self.assertEqual((pair["node_connectivity"], pair["edge_connectivity"]), (1, 2))
        self.assertEqual(r["metrics"]["shared_fate"], {"edge-pair": ["r1", "r2"]})
        self.assertEqual(pair["cut_set"], ["shared-fate:edge-pair"])

    def test_an_inferred_spof_is_proxy(self):
        t = uplink()
        t["nodes"][2]["evidence"] = "inferred: the ISP handoff is not in the configs"
        spof = next(f for f in NG.analyze(t)["findings"] if f["id"] == "NG-SPOF-r1")
        self.assertEqual(spof["confidence"], "proxy")

    def test_the_metric_keys_netreview_reads(self):
        m = NG.analyze(uplink(ha=True))["metrics"]
        self.assertEqual(m["critical_pairs"][0] | {"why": None, "single_points": None, "bridges": None},
                         {"from": "users", "to": "internet", "why": None, "node_connectivity": 2,
                          "edge_connectivity": 2, "cut_set": ["r1", "r2"], "single_points": None, "bridges": None})
        self.assertEqual((m["articulation_points"], m["bridges"], m["components"]), ([], [], 1))   # a 4-cycle
        self.assertIsInstance(m["hub_concentration"], float)
        self.assertEqual(set(m["betweenness"]), {"users", "internet", "r1", "r2"})
        self.assertLessEqual({"random", "degree", "betweenness"}, set(m["robustness"]))

    def test_a_disconnected_pair_and_one_below_target(self):
        t = uplink()
        t["edges"] = t["edges"][:1]
        r = NG.analyze(t)
        self.assertIn("NG-CUT-users-internet", ids(r))
        pair = r["metrics"]["critical_pairs"][0]
        self.assertEqual((pair["node_connectivity"], pair["edge_connectivity"], pair["cut_set"]), (0, 0, []))
        r = NG.analyze(uplink(ha=True), min_connectivity=3)
        self.assertEqual(ids(r, "NG-CONN"), ["NG-CONN-users-internet"])
        self.assertEqual(ids(r, "NG-SPOF"), [])

    def test_a_zone_endpoint_resolves_to_its_nodes(self):
        t = uplink()
        t["nodes"].append(node("users2", "lan", zone="corp"))
        t["nodes"][0]["zone"] = "corp"
        t["edges"].append(edge("e-users2-r1", "users2", "r1"))
        t["critical_pairs"] = [{"from": "corp", "to": "internet", "why": "staff browsing"}]
        r = NG.analyze(t)
        self.assertEqual(ids(r, "NG-SPOF"), ["NG-SPOF-r1"])
        self.assertEqual(ids(r, "NG-BRIDGE"), ["NG-BRIDGE-e-r1-isp"])  # users–r1 alone doesn't cut the zone


def two_spokes(peered):
    nodes = [node("hub", "vnet"), node("spoke-a", "vnet"), node("spoke-b", "vnet")]
    edges = [edge("p-a", "hub", "spoke-a", "peering")] + ([edge("p-b", "hub", "spoke-b", "peering")] if peered else [])
    nets = [{"id": "hub", "cidr": "10.0.0.0/16", "parent": None, "purpose": "hub", "evidence": "net.tf:1"},
            {"id": "spoke-a", "cidr": "10.1.0.0/16", "parent": None, "purpose": "a", "evidence": "net.tf:5"},
            {"id": "spoke-b", "cidr": "10.1.128.0/17", "parent": None, "purpose": "b", "evidence": "net.tf:9"}]
    return topo(nodes, edges, networks=nets)


class Addresses(unittest.TestCase):
    def test_overlap_is_caught_only_when_the_networks_are_reachable(self):
        r = NG.analyze(two_spokes(peered=True))
        self.assertEqual(ids(r, "NG-OVERLAP"), ["NG-OVERLAP-spoke-a-spoke-b"])
        self.assertEqual(r["findings"][0]["severity"], "High")
        r = NG.analyze(two_spokes(peered=False))
        self.assertEqual(ids(r, "NG-OVERLAP") + ids(r, "NG-DUP"), [])
        self.assertEqual(len(r["metrics"]["addresses"]["unreachable_overlaps"]), 1)

    def test_an_overlap_is_reported_once_at_the_enclosing_pair(self):
        t = two_spokes(peered=True)
        t["networks"][2]["cidr"] = "10.1.0.0/16"
        t["nodes"].append(node("snet-a", "subnet"))
        t["edges"].append(edge("l-a", "spoke-a", "snet-a", "l3-adjacency"))
        t["networks"].append({"id": "snet-a", "cidr": "10.1.1.0/24", "parent": "spoke-a", "evidence": "net.tf:7"})
        self.assertEqual(ids(NG.analyze(t)), ["NG-OVERLAP-spoke-a-spoke-b"])

    def test_a_duplicate_prefix_in_unreachable_networks_is_medium(self):
        t = two_spokes(peered=False)
        t["networks"][2]["cidr"] = "10.1.0.0/16"
        dup = [f for f in NG.analyze(t)["findings"] if f["id"].startswith("NG-DUP")]
        self.assertEqual([(f["id"], f["severity"]) for f in dup], [("NG-DUP-spoke-a-spoke-b", "Medium")])

    def test_a_subnet_inside_its_parent_is_not_an_overlap_and_one_outside_is_flagged(self):
        t = topo([node("vnet", "vnet"), node("snet", "subnet"), node("stray", "subnet")],
                 [edge("l1", "vnet", "snet", "l3-adjacency"), edge("l2", "vnet", "stray", "l3-adjacency")],
                 networks=[{"id": "vnet", "cidr": "10.20.0.0/16", "evidence": "n.tf:1"},
                           {"id": "snet", "cidr": "10.20.1.0/24", "parent": "vnet", "evidence": "n.tf:2"},
                           {"id": "stray", "cidr": "10.30.1.0/24", "parent": "vnet", "evidence": "n.tf:3"}])
        self.assertEqual(ids(NG.analyze(t)), ["NG-PARENT-stray"])

    def test_classification_and_public_ranges_used_internally(self):
        net = NG.ipaddress.ip_network
        self.assertEqual(NG.classify(net("172.20.0.0/16")), "rfc1918")
        self.assertEqual(NG.classify(net("100.64.10.0/24")), "rfc6598")
        self.assertEqual(NG.classify(net("8.8.8.0/24")), "public")
        self.assertEqual(NG.classify(net("0.0.0.0/0")), "mixed")
        t = topo([node("dmz", "lan")], [], networks=[{"id": "dmz", "cidr": "203.0.114.0/24", "evidence": "x:1"}])
        r = NG.analyze(t)
        self.assertEqual([(f["id"], f["severity"]) for f in r["findings"]], [("NG-PUBLIC-dmz", "Medium")])


def edge_zone(*flows):
    zones = [{"id": "internet", "trust": 0, "purpose": "untrusted"}, {"id": "app", "trust": 2, "purpose": "app"}]
    return topo([node("internet", "internet", zone="internet"), node("app", "lan", zone="app")],
                [edge("e1", "internet", "app")], zones=zones, flows=list(flows))


class Flows(unittest.TestCase):
    deny_all = flow("deny-all", "*", "*", "*", "deny", 4096, "any")

    def test_internet_to_ssh_allowed_is_critical(self):
        r = NG.analyze(edge_zone(flow("ssh", "internet", "app", "22"), self.deny_all))
        crit = [f for f in r["findings"] if f["severity"] == "Critical"]
        self.assertEqual([f["id"] for f in crit], ["NG-MGMT-ssh"])
        self.assertIn("SSH (22/tcp)", crit[0]["summary"])
        self.assertEqual(crit[0]["theory"], "theory §14")

    def test_a_higher_priority_deny_shadows_it(self):
        r = NG.analyze(edge_zone(flow("ssh", "internet", "app", "22", priority=200),
                                 flow("no-ssh", "internet", "*", "22", "deny", priority=100), self.deny_all))
        self.assertEqual(ids(r, "NG-MGMT"), [])

    def test_a_lower_priority_deny_does_not(self):
        r = NG.analyze(edge_zone(flow("ssh", "internet", "app", "22", priority=100),
                                 flow("no-ssh", "internet", "app", "22", "deny", priority=200), self.deny_all))
        self.assertEqual(ids(r, "NG-MGMT"), ["NG-MGMT-ssh"])

    def test_https_and_other_protocols_are_not_management(self):
        r = NG.analyze(edge_zone(flow("web", "internet", "app", "443"), flow("x", "internet", "app", "22", proto="udp"),
                                 self.deny_all))
        self.assertEqual(r["findings"], [])

    def test_a_port_range_and_any_source_expose_management(self):
        r = NG.analyze(edge_zone(flow("wide", "*", "app", "1-1024"), self.deny_all))
        self.assertEqual(ids(r, "NG-MGMT"), ["NG-MGMT-wide"])
        for name in ("SSH", "Telnet", "SNMP", "SMB"):
            self.assertIn(name, r["findings"][0]["summary"])
        self.assertNotIn("RDP", r["findings"][0]["summary"])

    def test_any_source_any_destination_allow(self):
        r = NG.analyze(edge_zone(flow("open", "*", "*", "443"), self.deny_all))
        self.assertEqual(ids(r, "NG-ANYANY"), ["NG-ANYANY-open"])

    def test_an_allow_pair_with_no_default_deny_is_high(self):
        r = NG.analyze(edge_zone(flow("web", "internet", "app", "443")))
        nodeny = [f for f in r["findings"] if f["id"].startswith("NG-NODENY")]
        self.assertEqual([(f["id"], f["severity"]) for f in nodeny], [("NG-NODENY-internet-app", "High")])
        for deny in (self.deny_all, flow("d", "*", "app", "*", "deny", 4096, "any"),
                     flow("d", "internet", "app", "*", "deny", 4096, "any")):
            self.assertEqual(ids(NG.analyze(edge_zone(flow("web", "internet", "app", "443"), deny)), "NG-NODENY"), [])
        partial = flow("d", "internet", "app", "22", "deny", 4096, "tcp")
        self.assertEqual(ids(NG.analyze(edge_zone(flow("web", "internet", "app", "443"), partial)), "NG-NODENY"),
                         ["NG-NODENY-internet-app"])

    def test_an_inferred_allow_is_proxy(self):
        r = NG.analyze(edge_zone(flow("ssh", "internet", "app", "22", evidence="inferred: no NSG attached"),
                                 self.deny_all))
        self.assertEqual([(f["severity"], f["confidence"]) for f in r["findings"]], [("Critical", "proxy")])

    def test_ports(self):
        self.assertEqual(NG.parse_ports("22,3389"), [(22, 22), (3389, 3389)])
        self.assertEqual(NG.parse_ports("1024-65535"), [(1024, 65535)])
        self.assertEqual(NG.parse_ports("*"), [(0, 65535)])
        for bad in ("ssh", "70000", "10-5", ""):
            self.assertRaises(ValueError, NG.parse_ports, bad)


class Validate(unittest.TestCase):
    def test_a_clean_topology_has_no_errors(self):
        self.assertEqual(NG.validate(uplink()), [])

    def test_each_schema_error(self):
        t = uplink()
        t["meta"].pop("rubric")
        t["nodes"].append(node("r1"))                                           # duplicate id
        t["nodes"][0]["zone"] = "nowhere"                                       # zones given below
        t["zones"] = [{"id": "internet"}]
        t["edges"].append(edge("e-x", "r1", "ghost"))
        t["edges"].append({"id": "e-y", "a": "r1", "b": "users", "kind": "l2-link"})   # no evidence
        t["networks"] = [{"id": "users", "cidr": "10.0.0.0/33", "evidence": "x:1"},
                         {"id": "orphan", "cidr": "10.1.0.0/24", "evidence": "x:2"}]
        t["critical_pairs"].append({"from": "users", "to": "nobody"})
        t["flows"] = [flow("f", "internet", "mars", "http")]
        errs = "\n".join(NG.validate(t))
        for want in ("missing field 'rubric'", "duplicate id", "unknown zone 'nowhere'", "unknown node 'ghost'",
                     "missing field 'evidence'", "unparseable CIDR", "orphan): no node with the same id",
                     "unknown node or zone 'nobody'", "unknown zone 'mars'", "unparseable ports 'http'"):
            self.assertIn(want, errs)

    def test_a_pair_whose_ends_meet_is_an_error(self):
        t = uplink(ha=True, shared_fate=True)
        t["critical_pairs"] = [{"from": "r1", "to": "r2", "why": "same box"}]
        self.assertIn("share a node or shared-fate group", "\n".join(NG.validate(t)))

    def test_schema_errors_stop_the_analysis(self):
        r = NG.analyze({"meta": {}})
        self.assertTrue(r["errors"])
        self.assertEqual((r["metrics"], r["findings"]), ({}, []))

    def test_analyze_never_raises_on_malformed_input(self):
        junk = [None, 0, "x", [], [1], {}, {"id": []}, {"id": "n"}, True, -1, "inferred: x", {"a": 1}]
        base = uplink(ha=True)
        base.update(zones=[{"id": "internet"}], flows=[flow("f", "internet", "*", "22")],
                    networks=[{"id": "users", "cidr": "10.0.0.0/24", "evidence": "x:1"}])
        cases = [None, [], "x", 3, {"meta": None, "nodes": None, "edges": None}]
        for key in ("meta", "nodes", "edges", "networks", "zones", "flows", "critical_pairs"):
            for value in junk:
                cases.append({**base, key: value})
                section = base[key]
                if isinstance(section, list):
                    for field in {f for el in section for f in el}:
                        for bad in junk:
                            el = {**section[0], field: bad}
                            cases.append({**base, key: [el, *section[1:]]})
                elif isinstance(section, dict):
                    for field in section:
                        cases.append({**base, key: {**section, field: [1]}})
        for case in cases:
            with self.subTest(case=json.dumps(case, default=str)[:120]):
                r = NG.analyze(case)
                self.assertEqual(set(r), {"metrics", "findings", "errors"})
                if r["errors"]:
                    self.assertEqual((r["metrics"], r["findings"]), ({}, []))


class CLI(unittest.TestCase):
    def run_cli(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                code = NG.main(list(args))
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()

    def test_exit_codes_and_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = pathlib.Path(tmp, "good.json"), pathlib.Path(tmp, "bad.json")
            good.write_text(json.dumps(uplink()))
            bad.write_text(json.dumps({"nodes": []}))
            code, out = self.run_cli("analyze", str(good), "--json")
            self.assertEqual(code, NG.EXIT_OK, out)
            self.assertIn("NG-SPOF-r1", [f["id"] for f in json.loads(out)["findings"]])
            code, out = self.run_cli("analyze", str(good), "--md")
            self.assertEqual(code, NG.EXIT_OK)
            self.assertIn("| NG-SPOF-r1 |", out)
            self.assertIn("## Robustness (G9)", out)
            self.assertEqual(self.run_cli("analyze", str(bad))[0], NG.EXIT_ERROR)
            self.assertEqual(self.run_cli("analyze", str(pathlib.Path(tmp, "missing.json")))[0], NG.EXIT_USAGE)
            self.assertEqual(self.run_cli("analyze", str(good), "--json", "--md")[0], NG.EXIT_USAGE)
            self.assertEqual(self.run_cli()[0], NG.EXIT_USAGE)


if __name__ == "__main__":
    unittest.main()
