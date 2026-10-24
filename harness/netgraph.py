#!/usr/bin/env python3
"""Compute what a network audit can decide from topology.json alone: graph metrics, address and flow checks.

    python3 harness/netgraph.py analyze topology.json            # Markdown report (the default, or --md)
    python3 harness/netgraph.py analyze topology.json --json     # {metrics, findings, errors}

    topology.json → validate → graph ─────────────────────► findings + metrics
    (netaudit's      schema    components, cut vertices       each {id, object, severity, confidence,
    recovered or     errors    and bridges, betweenness,      theory, evidence, summary}
    proposed model)  stop it   Menger per critical pair,
                               robustness curves
                             → addresses → flows

The contract is skills/networking/netaudit/topology-modeling.md. Computed here, never judged:
- **cut vertices and bridges** (Tarjan, G4) on the undirected multigraph, so parallel edges are never
  bridges;
- **Menger connectivity** (G5) of each critical pair by unit-capacity max-flow, with every
  `attrs.shared_fate` group contracted to one node: an HA pair that fails together counts once. A pair
  below --min-connectivity names the nodes and edges whose loss alone disconnects it;
- **betweenness** (Brandes, G6), the degree distribution and hub concentration, and **robustness curves**
  (G9): the largest-component fraction as 0–50% of nodes are removed at random (seeded, averaged over
  --runs) or by attack (highest degree / highest betweenness first, ranked once on the intact graph);
- **addresses** (§3): overlap between networks the graph connects, a subnet outside its parent, duplicate
  prefixes, and RFC1918 / RFC6598 / public classification;
- **flows** (§11, §14): management ports allowed from the internet and not shadowed by an earlier deny
  (strictly lower priority), any-source allows, and zone pairs that allow traffic with no deny behind it.

A finding that rests only on elements whose evidence is `inferred: …` is never ✅ decidable: it is ⚠️ proxy.
Stdlib only, no model calls. Exit status: 0 done · 1 schema errors · 2 usage.
"""
from __future__ import annotations

import argparse
import collections
import ipaddress
import itertools
import json
import math
import pathlib
import random
import re
import sys

EXIT_OK, EXIT_ERROR, EXIT_USAGE = 0, 1, 2
NODE_KINDS = ("internet", "onprem", "site", "router", "switch", "firewall", "gateway", "lb", "dns", "dhcp",
              "proxy", "vnet", "subnet", "lan", "cluster", "namespace", "host-group", "private-endpoint", "service")
EDGE_KINDS = ("l2-link", "l3-adjacency", "peering", "vpn", "route")
PROTOS = ("tcp", "udp", "icmp", "any")
ACTIONS = ("allow", "deny")
SEVERITIES = ("Critical", "High", "Medium", "Low")
META = ("name", "source_version", "rubric", "stage", "status")
REQUIRED = {
    "nodes": ("id", "kind", "evidence"),
    "edges": ("id", "a", "b", "kind", "evidence"),
    "networks": ("id", "cidr", "evidence"),
    "zones": ("id",),
    "flows": ("id", "from_zone", "to_zone", "proto", "ports", "action", "priority", "evidence"),
    "critical_pairs": ("from", "to"),
}
STRINGS = ("id", "a", "b", "kind", "cidr", "from_zone", "to_zone", "proto", "action", "from", "to", "zone", "parent")
INTERNET, ANY = "internet", "*"
# A management service: its port → the protocols it answers on, and its name.
MGMT = {22: (("tcp",), "SSH"), 23: (("tcp",), "Telnet"), 161: (("udp", "tcp"), "SNMP"), 445: (("tcp",), "SMB"),
        3389: (("tcp", "udp"), "RDP"), 5985: (("tcp",), "WinRM"), 5986: (("tcp",), "WinRM/TLS")}
RANGES = (("rfc1918", ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")), ("rfc6598", ("100.64.0.0/10",)),
          ("ula", ("fc00::/7",)))
RANGES = tuple((name, tuple(ipaddress.ip_network(b) for b in blocks)) for name, blocks in RANGES)
FRACTIONS = tuple(i / 20 for i in range(11))     # 0%, 5%, … 50% of nodes removed
HUB_SHARE = 0.10                                 # hub concentration: the top 10% of nodes by degree
INF = 10 ** 9
THEORY = {"spof": "graph-theory G4", "bridge": "graph-theory G4", "cut": "graph-theory G5",
          "conn": "graph-theory G5", "address": "theory §3", "mgmt": "theory §14", "policy": "theory §11"}
CONFIDENCE_MARK = {"decidable": "✅", "proxy": "⚠️", "needs-data": "🔬"}


# ------------------------------------------------------------------ validate

def _items(t, key):
    v = t.get(key)
    return v if isinstance(v, list) else []


def _missing(el, field):
    return el.get(field) is None or el.get(field) == ""


def parse_ports(spec):
    """'443' | '1024-65535' | '22,3389' | '*' → [(lo, hi), …]. ValueError on anything else."""
    spec = str(spec).strip()
    if spec in (ANY, "any"):
        return [(0, 65535)]
    out = []
    for part in spec.split(","):
        lo, _, hi = part.strip().partition("-")
        lo, hi = int(lo), int(hi or lo)
        if not 0 <= lo <= hi <= 65535:
            raise ValueError(f"port range {part.strip()!r} is outside 0–65535 or reversed")
        out.append((lo, hi))
    return out


def validate(t):
    """Schema errors as strings; empty when the topology can be analysed."""
    if not isinstance(t, dict):
        return ["topology: not a JSON object"]
    errs = []
    meta = t.get("meta")
    if not isinstance(meta, dict):
        errs.append("meta: missing")
    else:
        errs += [f"meta: missing field '{k}'" for k in META if _missing(meta, k)]
    errs += [f"{k}: missing (a list is required)" for k in ("nodes", "edges") if not isinstance(t.get(k), list)]
    errs += [f"{k}: not a list" for k in ("networks", "zones", "flows", "critical_pairs")
             if k in t and not isinstance(t[k], list)]

    ids, ok = {}, {}
    for key, fields in REQUIRED.items():
        ids[key], ok[key] = set(), []
        for i, el in enumerate(_items(t, key)):
            if not isinstance(el, dict):
                errs.append(f"{key}[{i}]: not an object")
                continue
            where = f"{key}[{i}]" + (f" ({el['id']})" if isinstance(el.get("id"), str) else "")
            bad = [f for f in fields if _missing(el, f)]
            errs += [f"{where}: missing field '{f}'" for f in bad]
            wrong = [f for f in STRINGS if el.get(f) is not None and not isinstance(el[f], str)]
            errs += [f"{where}: {f} must be a string" for f in wrong]
            if wrong:
                continue
            if "attrs" in el and not isinstance(el["attrs"], dict):
                errs.append(f"{where}: attrs must be an object")
                continue
            if "id" in fields and el.get("id") in ids[key]:
                errs.append(f"{where}: duplicate id")
            elif isinstance(el.get("id"), str):
                ids[key].add(el["id"])
            if not bad:
                ok[key].append((where, el))

    node_ids, net_ids = ids["nodes"], ids["networks"]
    zones_given = isinstance(t.get("zones"), list)
    zone_ids = ids["zones"] | ({n.get("zone") for _, n in ok["nodes"] if n.get("zone")} if not zones_given else set())
    for where, n in ok["nodes"]:
        if n["kind"] not in NODE_KINDS and not (n.get("attrs") or {}).get("note"):
            errs.append(f"{where}: unknown kind '{n['kind']}' (say why none fits in attrs.note)")
        if zones_given and n.get("zone") is not None and n["zone"] not in zone_ids:
            errs.append(f"{where}: unknown zone '{n['zone']}'")
    for where, e in ok["edges"]:
        errs += [f"{where}: {end} names unknown node '{e[end]}'" for end in ("a", "b") if e[end] not in node_ids]
        if e["kind"] not in EDGE_KINDS:
            errs.append(f"{where}: unknown kind '{e['kind']}' (one of {', '.join(EDGE_KINDS)})")
    for where, n in ok["networks"]:
        try:
            ipaddress.ip_network(str(n["cidr"]), strict=False)
        except ValueError:
            errs.append(f"{where}: unparseable CIDR '{n['cidr']}'")
        if n["id"] not in node_ids:
            errs.append(f"{where}: no node with the same id (every network is also a node)")
        if n.get("parent") and n["parent"] not in net_ids:
            errs.append(f"{where}: parent '{n['parent']}' is not a network")
    for where, f in ok["flows"]:
        if f["proto"] not in PROTOS:
            errs.append(f"{where}: unknown proto '{f['proto']}' (one of {', '.join(PROTOS)})")
        if f["action"] not in ACTIONS:
            errs.append(f"{where}: unknown action '{f['action']}' (allow or deny)")
        if not isinstance(f["priority"], int) or isinstance(f["priority"], bool):
            errs.append(f"{where}: priority must be an integer")
        try:
            parse_ports(f["ports"])
        except ValueError:
            errs.append(f"{where}: unparseable ports '{f['ports']}'")
        if zones_given:
            errs += [f"{where}: {end} names unknown zone '{f[end]}'" for end in ("from_zone", "to_zone")
                     if f[end] != ANY and f[end] not in zone_ids]
    in_zone = collections.defaultdict(list)
    for _, n in ok["nodes"]:
        in_zone[n.get("zone")].append(n["id"])
    rep = shared_fate_reps(n for _, n in ok["nodes"])
    for where, cp in ok["critical_pairs"]:
        ends = []
        for end in ("from", "to"):
            v = cp[end]
            if v in node_ids:
                ends.append({rep.get(v, v)})
            elif v not in zone_ids:
                errs.append(f"{where}: {end} names unknown node or zone '{v}'")
            elif not in_zone[v]:
                errs.append(f"{where}: {end} names zone '{v}', which has no nodes")
            else:
                ends.append({rep.get(x, x) for x in in_zone[v]})
        if len(ends) == 2 and ends[0] & ends[1]:
            errs.append(f"{where}: from and to share a node or shared-fate group, so connectivity is undefined")
    return errs


def shared_fate_reps(nodes):
    """node id → its shared-fate group's representative, 'shared-fate:<group>'."""
    return {n["id"]: f"shared-fate:{n['attrs']['shared_fate']}" for n in nodes
            if isinstance(n.get("attrs"), dict) and n["attrs"].get("shared_fate")}


# ------------------------------------------------------------------ graph

def _adjacency(nodes, edges):
    """Multigraph adjacency, v → [(neighbour, edge id)]. Self-loops are dropped: they connect nothing."""
    adj = {v: [] for v in nodes}
    for e, a, b in edges:
        if a != b:
            adj[a].append((b, e))
            adj[b].append((a, e))
    return adj


def _simple(nodes, edges):
    return {v: {w for w, _ in nbrs} for v, nbrs in _adjacency(nodes, edges).items()}


def degrees(nodes, edges):
    return {v: len(nbrs) for v, nbrs in _adjacency(nodes, edges).items()}


def components(nodes, edges):
    """Connected components, largest first, each a sorted list."""
    adj, seen, out = _simple(nodes, edges), set(), []
    for root in nodes:
        if root in seen:
            continue
        seen.add(root)
        comp, queue = [], collections.deque([root])
        while queue:
            v = queue.popleft()
            comp.append(v)
            for w in adj[v] - seen:
                seen.add(w)
                queue.append(w)
        out.append(sorted(comp))
    return sorted(out, key=lambda c: (-len(c), c[0]))


def cut_structure(nodes, edges):
    """Articulation points and bridges (Tarjan), iteratively. The DFS skips only the edge it arrived by,
    not every edge back to its parent, so a parallel edge is a back edge and never a bridge."""
    adj = _adjacency(nodes, edges)
    disc, low, aps, bridges, clock = {}, {}, set(), [], 0
    for root in nodes:
        if root in disc:
            continue
        disc[root] = low[root] = clock
        clock += 1
        children, stack = 0, [(root, None, iter(adj[root]))]
        while stack:
            v, via, it = stack[-1]
            for w, e in it:
                if e == via:
                    continue
                if w in disc:
                    low[v] = min(low[v], disc[w])
                else:
                    disc[w] = low[w] = clock
                    clock += 1
                    stack.append((w, e, iter(adj[w])))
                    break
            else:
                stack.pop()
                if not stack:
                    continue
                u = stack[-1][0]
                low[u] = min(low[u], low[v])
                if low[v] > disc[u]:
                    bridges.append(via)
                if u == root:
                    children += 1
                elif low[v] >= disc[u]:
                    aps.add(u)
        if children > 1:
            aps.add(root)
    return sorted(aps), sorted(bridges)


def betweenness(nodes, edges):
    """Brandes betweenness on the simple graph, normalised by (n−1)(n−2)/2 unordered pairs."""
    adj, bc = _simple(nodes, edges), dict.fromkeys(nodes, 0.0)
    for s in nodes:
        order, pred, sigma, dist = [], collections.defaultdict(list), collections.Counter({s: 1}), {s: 0}
        queue = collections.deque([s])
        while queue:
            v = queue.popleft()
            order.append(v)
            for w in adj[v]:
                if w not in dist:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta = collections.Counter()
        for w in reversed(order):
            for v in pred[w]:
                delta[v] += sigma[v] / sigma[w] * (1 + delta[w])
            if w != s:
                bc[w] += delta[w]
    n = len(nodes)
    scale = 1 / ((n - 1) * (n - 2)) if n > 2 else 0.0   # each unordered pair was counted from both ends
    return {v: bc[v] * scale for v in nodes}


def contract(nodes, edges, rep):
    """Merge each node into its representative; edges inside one group disappear, parallels stay."""
    cnodes = list(dict.fromkeys(rep.get(v, v) for v in nodes))
    cedges = [(e, rep.get(a, a), rep.get(b, b)) for e, a, b in edges if rep.get(a, a) != rep.get(b, b)]
    return cnodes, cedges


def _maxflow(cap, s, t):
    flow = 0
    while True:
        prev, queue = {s: None}, collections.deque([s])
        while queue and t not in prev:
            u = queue.popleft()
            for v, c in cap[u].items():
                if c > 0 and v not in prev:
                    prev[v] = u
                    queue.append(v)
        if t not in prev:
            return flow
        path, v = [], t
        while prev[v] is not None:
            path.append((prev[v], v))
            v = prev[v]
        push = min(cap[u][v] for u, v in path)
        for u, v in path:
            cap[u][v] -= push
            cap[v][u] += push
        flow += push


def _flow_network(nodes, edges, S, T, split):
    """Unit capacities. With `split`, every node but the endpoints is an in→out arc of capacity 1, and
    an edge is capacity 1 only between two endpoints (a direct path) — elsewhere its node already
    bounds it, so a minimum cut names nodes. Returns the capacities and, per arc, the edge ids it
    carries (parallel edges share an arc)."""
    cap, carries = collections.defaultdict(lambda: collections.defaultdict(int)), collections.defaultdict(list)

    def arc(u, v, c):
        cap[u][v] += c
        cap[v][u] += 0

    def end(v, side):
        return (side, v) if split and v not in S and v not in T else ("node", v)

    if split:
        for v in nodes:
            if v not in S and v not in T:
                arc(("in", v), ("out", v), 1)
    for e, a, b in edges:
        if a != b:
            direct = not split or {a, b} <= S | T
            for u, v in ((a, b), (b, a)):
                arc(end(u, "out"), end(v, "in"), 1 if direct else INF)
                carries[(end(u, "out"), end(v, "in"))].append(e)
    for v in S:
        arc(("source",), ("node", v), INF)
    for v in T:
        arc(("node", v), ("sink",), INF)
    return cap, carries


def connectivity(nodes, edges, sources, targets):
    """(node, edge) connectivity between two node sets by unit-capacity max-flow (Menger). Node
    connectivity counts paths with no internal node in common; endpoints are never cut. None when
    the sets meet."""
    S, T = set(sources), set(targets)
    if S & T:
        return None, None
    return tuple(_maxflow(_flow_network(nodes, edges, S, T, split)[0], ("source",), ("sink",))
                 for split in (True, False))


def min_cut(nodes, edges, sources, targets):
    """A minimum set of nodes and edges whose loss disconnects the sets: as many as the node
    connectivity. Edges appear only where no internal node can be cut (a direct source–target edge).
    Empty when the sets are already disconnected or meet."""
    S, T = set(sources), set(targets)
    if S & T:
        return []
    cap, carries = _flow_network(nodes, edges, S, T, True)
    _maxflow(cap, ("source",), ("sink",))
    side, queue = {("source",)}, collections.deque([("source",)])
    while queue:
        u = queue.popleft()
        for v, c in cap[u].items():
            if c > 0 and v not in side:
                side.add(v)
                queue.append(v)
    cut = []
    for u in side:
        for v in cap[u]:
            if v in side:
                continue
            if u[0] == "in" and v == ("out", u[1]):
                cut.append(u[1])
            else:
                cut += carries.get((u, v), [])
    return sorted(set(cut))


def _reaches(adj, S, T, skip_node=None, skip_edge=None):
    seen = set(S)
    queue = collections.deque(S)
    while queue:
        v = queue.popleft()
        if v in T:
            return True
        for w, e in adj[v]:
            if w != skip_node and e != skip_edge and w not in seen:
                seen.add(w)
                queue.append(w)
    return False


def separators(nodes, edges, sources, targets):
    """The nodes and edges whose loss alone disconnects every source from every target. Each one
    must be a cut vertex or a bridge of the whole graph, so only those are tried."""
    S, T = set(sources), set(targets)
    aps, bridges = cut_structure(nodes, edges)
    adj = _adjacency(nodes, edges)
    return ([v for v in aps if v not in S and v not in T and not _reaches(adj, S, T, skip_node=v)],
            [e for e in bridges if not _reaches(adj, S, T, skip_edge=e)])


def giant_curve(nodes, adj, order, fractions=FRACTIONS):
    """Largest-component fraction after removing order[:k], for k = ⌊f·n⌋, by adding nodes back in
    reverse into a union-find."""
    n = len(nodes)
    if not n:
        return [0.0 for _ in fractions]
    parent, size, best, after = {}, {}, 0, [0] * (n + 1)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for k in range(n - 1, -1, -1):
        v = order[k]
        parent[v], size[v] = v, 1
        for w in adj[v]:
            if w in parent:
                a, b = find(v), find(w)
                if a != b:
                    if size[a] < size[b]:
                        a, b = b, a
                    parent[b] = a
                    size[a] += size[b]
        best = max(best, size[find(v)])
        after[k] = best
    return [after[int(f * n + 1e-9)] / n for f in fractions]


def robustness(nodes, edges, bc=None, *, seed=0, runs=20):
    """Random failure (seeded, mean of `runs` shuffles) against targeted attack, ranked once on the
    intact graph by degree and by betweenness."""
    adj, deg = _simple(nodes, edges), degrees(nodes, edges)
    bc = bc if bc is not None else betweenness(nodes, edges)
    rng, base, rand = random.Random(seed), sorted(nodes), [0.0] * len(FRACTIONS)
    for _ in range(runs):
        order = base[:]
        rng.shuffle(order)
        rand = [r + x / runs for r, x in zip(rand, giant_curve(nodes, adj, order))]
    by_degree = sorted(nodes, key=lambda v: (-deg[v], v))
    by_bc = sorted(nodes, key=lambda v: (-bc[v], -deg[v], v))
    return {"fractions": list(FRACTIONS), "random": _r(rand), "degree": _r(giant_curve(nodes, adj, by_degree)),
            "betweenness": _r(giant_curve(nodes, adj, by_bc)), "seed": seed, "runs": runs}


def _r(xs, nd=4):
    return [round(x, nd) for x in xs]


def graph_metrics(nodes, edges, *, seed=0, runs=20):
    comps = components(nodes, edges)
    aps, bridges = cut_structure(nodes, edges)
    bc, deg = betweenness(nodes, edges), degrees(nodes, edges)
    n, ends = len(nodes), sum(deg.values())
    top = sorted(nodes, key=lambda v: (-deg[v], v))[:max(1, math.ceil(HUB_SHARE * n))] if n else []
    return {
        "components": len(comps),
        "component_sizes": [len(c) for c in comps],
        "largest_component_fraction": round(len(comps[0]) / n, 4) if n else 0.0,
        "component_members": comps if len(comps) > 1 else [],
        "articulation_points": aps,
        "bridges": bridges,
        "betweenness": {v: round(bc[v], 4) for v in sorted(nodes, key=lambda v: (-bc[v], v))},
        "degree": {"distribution": {str(k): c for k, c in sorted(collections.Counter(deg.values()).items())},
                   "max": max(deg.values(), default=0), "mean": round(ends / n, 4) if n else 0.0,
                   "hub_nodes": top},
        "hub_concentration": round(sum(deg[v] for v in top) / ends, 4) if ends else 0.0,
        "robustness": robustness(nodes, edges, bc, seed=seed, runs=runs),
    }


# ------------------------------------------------------------------ findings

def _inferred(evidence):
    return str(evidence or "").strip().lower().startswith("inferred")


def _slug(s):
    return re.sub(r"[^\w.-]+", "_", "any" if s == ANY else str(s))


def finding(fid, obj, severity, theory, elements, summary, confidence=None):
    """`elements` are what the finding rests on; one inferred element makes it ⚠️ proxy, never ✅ decidable."""
    evidence = list(dict.fromkeys(str(el.get("evidence", "")) for el in elements))
    if confidence is None:
        confidence = "proxy" if any(_inferred(e) for e in evidence) else "decidable"
    return {"id": fid, "object": obj, "severity": severity, "confidence": confidence, "theory": THEORY[theory],
            "evidence": "; ".join(evidence), "summary": summary}


def resilience(t, nodes, edges, min_k):
    """Connectivity per critical pair on the shared-fate-contracted graph, and the SPOF / bridge findings."""
    rep, groups = shared_fate_reps(nodes.values()), collections.defaultdict(list)
    for v, g in rep.items():
        groups[g].append(v)
    cnodes, cedges = contract(list(nodes), edges, rep)
    in_zone = collections.defaultdict(list)
    for v, n in nodes.items():
        in_zone[n.get("zone")].append(v)
    edge_el = {e["id"]: e for e in t["edges"]}

    def resolve(x):
        return {rep.get(v, v) for v in ([x] if x in nodes else in_zone[x])}

    pairs, spof, cut_edges, out = [], collections.defaultdict(list), collections.defaultdict(list), []
    for cp in _items(t, "critical_pairs"):
        S, T = resolve(cp["from"]), resolve(cp["to"])
        label = f"{cp['from']} → {cp['to']}"
        k_node, k_edge = connectivity(cnodes, cedges, S, T)
        sep_nodes, sep_edges = separators(cnodes, cedges, S, T) if k_node == 1 else ([], [])
        pairs.append({"from": cp["from"], "to": cp["to"], "why": cp.get("why", ""), "node_connectivity": k_node,
                      "edge_connectivity": k_edge, "cut_set": min_cut(cnodes, cedges, S, T),
                      "single_points": sep_nodes, "bridges": sep_edges})
        ends = [nodes[v] for v in sorted({v for x in (cp["from"], cp["to"])
                                           for v in ([x] if x in nodes else in_zone[x])})]
        if k_node == 0:
            out.append(finding(f"NG-CUT-{_slug(cp['from'])}-{_slug(cp['to'])}", f"critical pair {label}", "High",
                               "cut", ends, f"No path joins {label} in the model ({cp.get('why') or 'critical pair'}): "
                               "either the evidence is missing a link or the service has none.", confidence="proxy"))
        elif k_node == 1 and min_k > 1:
            for v in sep_nodes:
                spof[v].append(label)
            for e in sep_edges:
                cut_edges[e].append(label)
        elif k_node < min_k:
            out.append(finding(f"NG-CONN-{_slug(cp['from'])}-{_slug(cp['to'])}", f"critical pair {label}", "Medium",
                               "conn", ends, f"{label} has node connectivity {k_node} and edge connectivity "
                               f"{k_edge}, below the target of {min_k}."))
    for v, labels in sorted(spof.items()):
        members = groups.get(v, [v])
        if v in groups:
            name = v.split(":", 1)[1]
            obj = f"shared-fate group {name} ({', '.join(members)})"
            what = (f"Shared-fate group {name} ({', '.join(members)}) fails as one, so its members' redundancy "
                    "does not count:")
        else:
            name, obj, what = v, v, f"{v} is a single point of failure:"
        out.append(finding(f"NG-SPOF-{_slug(name)}", obj, "High", "spof", [nodes[m] for m in members],
                           f"{what} losing it disconnects {', '.join(labels)} (node connectivity 1 < {min_k})."))
    for e, labels in sorted(cut_edges.items()):
        el = edge_el[e]
        out.append(finding(f"NG-BRIDGE-{_slug(e)}", f"{e} ({el['a']} — {el['b']}, {el['kind']})", "High", "bridge",
                           [el], f"{e} is a bridge: losing it disconnects {', '.join(labels)} "
                           f"(edge connectivity 1 < {min_k}); no parallel link backs it up."))
    return pairs, {g.split(":", 1)[1]: m for g, m in groups.items()}, out


def classify(net):
    for name, blocks in RANGES:
        if any(net.version == b.version and net.subnet_of(b) for b in blocks):
            return name
    if any(net.version == b.version and net.overlaps(b) for _, blocks in RANGES for b in blocks):
        return "mixed"
    return "public" if net.is_global else "special"


def address_checks(t, nodes, component_of):
    nets = {n["id"]: n for n in _items(t, "networks")}
    cidr = {i: ipaddress.ip_network(str(n["cidr"]), strict=False) for i, n in nets.items()}
    cls = {i: classify(c) for i, c in cidr.items()}

    def ancestors(i):
        seen, p = set(), nets[i].get("parent")
        while p in nets and p not in seen:
            seen.add(p)
            p = nets[p].get("parent")
        return seen

    anc = {i: ancestors(i) for i in nets}

    def clash(x, y):
        a, b = cidr[x], cidr[y]
        return a.version == b.version and a.overlaps(b) and x not in anc[y] and y not in anc[x]

    def inherited(x, y):
        """An enclosing pair already clashes the same way, so this one is its consequence, not a new finding."""
        return any((p, q) != (x, y) and clash(p, q) and (component_of[p] == component_of[q]) ==
                   (component_of[x] == component_of[y]) for p in anc[x] | {x} for q in anc[y] | {y})

    out, unreachable = [], []
    for x, y in itertools.combinations(sorted(nets), 2):
        if not clash(x, y) or inherited(x, y):
            continue
        a, b = cidr[x], cidr[y]
        same = "the same prefix" if a == b else "overlapping prefixes"
        if component_of[x] == component_of[y]:
            out.append(finding(f"NG-OVERLAP-{_slug(x)}-{_slug(y)}", f"{x} ({a}) ∩ {y} ({b})", "High", "address",
                               [nets[x], nets[y]], f"{x} and {y} use {same} and the graph connects them: "
                               "routing between them cannot tell the two apart."))
        elif a == b:
            out.append(finding(f"NG-DUP-{_slug(x)}-{_slug(y)}", f"{x} = {y} ({a})", "Medium", "address",
                               [nets[x], nets[y]], f"{x} and {y} use the same prefix {a}. They are not "
                               "connected today; peering, VPN or a merger would make it an overlap."))
        else:
            unreachable.append({"a": x, "b": y, "a_cidr": str(a), "b_cidr": str(b)})
    for i in sorted(nets):
        p = nets[i].get("parent")
        if p in cidr and (cidr[i].version != cidr[p].version or not cidr[i].subnet_of(cidr[p])):
            out.append(finding(f"NG-PARENT-{_slug(i)}", f"{i} ({cidr[i]}) ⊄ {p} ({cidr[p]})", "Medium", "address",
                               [nets[i], nets[p]], f"{i} ({cidr[i]}) lies outside its parent {p} "
                               f"({cidr[p]}): the parent's aggregate does not cover it."))
        node = nodes[i]
        if cls[i] == "public" and node.get("zone") != INTERNET and node["kind"] != "internet":
            out.append(finding(f"NG-PUBLIC-{_slug(i)}", f"{i} ({cidr[i]})", "Medium", "address", [nets[i]],
                               f"{i} uses public range {cidr[i]} internally: unless the organisation holds that "
                               "allocation, its hosts shadow the real owners."))
    metrics = {"networks": {i: {"cidr": str(cidr[i]), "class": cls[i]} for i in sorted(nets)},
               "by_class": dict(sorted(collections.Counter(cls.values()).items())),
               "unreachable_overlaps": unreachable}
    return metrics, out


def _covers(flow, proto, port):
    return flow["proto"] in ("any", proto) and any(lo <= port <= hi for lo, hi in parse_ports(flow["ports"]))


def _all_ports(spec):
    reach = 1
    for lo, hi in sorted(parse_ports(spec)):
        if lo > reach:
            return False
        reach = max(reach, hi + 1)
    return reach > 65535


def flow_checks(t, nodes):
    flows = _items(t, "flows")
    allows = sorted((f for f in flows if f["action"] == "allow"), key=lambda f: (f["priority"], f["id"]))
    denies = [f for f in flows if f["action"] == "deny"]
    has_internet = any(n["kind"] == "internet" or n.get("zone") == INTERNET for n in nodes.values()) or \
        any(z.get("id") == INTERNET for z in _items(t, "zones"))
    from_internet = {INTERNET, ANY} if has_internet else {INTERNET}
    out = []

    def shadowed(f, proto, port):
        return any(d["priority"] < f["priority"] and d["from_zone"] in (ANY, INTERNET)
                   and d["to_zone"] in (ANY, f["to_zone"]) and _covers(d, proto, port) for d in denies)

    for f in allows:
        if f["from_zone"] not in from_internet or f["to_zone"] == INTERNET:
            continue
        exposed = [f"{name} ({port}/{'/'.join(p for p in protos if _covers(f, p, port))})"
                   for port, (protos, name) in MGMT.items()
                   if any(_covers(f, p, port) and not shadowed(f, p, port) for p in protos)]
        if exposed:
            out.append(finding(f"NG-MGMT-{_slug(f['id'])}", f"flow {f['id']} ({f['from_zone']} → {f['to_zone']})",
                               "Critical", "mgmt", [f], f"Allows {', '.join(exposed)} from the internet to zone "
                               f"{f['to_zone']}, and no earlier deny shadows it."))
    for f in allows:
        if f["from_zone"] == ANY and f["proto"] != "icmp" and (f["to_zone"] == ANY or _all_ports(f["ports"])):
            dest = "any destination" if f["to_zone"] == ANY else f"every port of zone {f['to_zone']}"
            out.append(finding(f"NG-ANYANY-{_slug(f['id'])}", f"flow {f['id']} ({ANY} → {f['to_zone']})", "High",
                               "policy", [f], f"Allows any source to {dest} ({f['proto']} {f['ports']}): "
                               "least privilege names who may connect."))
    pairs = collections.defaultdict(list)
    for f in allows:
        pairs[(f["from_zone"], f["to_zone"])].append(f)
    full_denies = [d for d in denies if d["proto"] == "any" and _all_ports(d["ports"])]
    open_pairs = []
    for (src, dst), fs in sorted(pairs.items()):
        if any(d["from_zone"] in (ANY, src) and d["to_zone"] in (ANY, dst) for d in full_denies):
            continue
        open_pairs.append(f"{src} → {dst}")
        grounded = [f for f in fs if not _inferred(f["evidence"])] or fs     # one recorded allow is enough
        out.append(finding(f"NG-NODENY-{_slug(src)}-{_slug(dst)}", f"zone pair {src} → {dst}", "High", "policy",
                           grounded, f"{src} → {dst} carries {len(fs)} allow flow(s) "
                           f"({', '.join(f['id'] for f in fs)}) and no deny of all traffic covers the pair: "
                           "what is not allowed is not denied."))
    metrics = {"total": len(flows), "allow": len(allows), "deny": len(denies), "pairs_without_deny": open_pairs}
    return metrics, out


# ------------------------------------------------------------------ analyze

def analyze(topology, *, seed=0, runs=20, min_connectivity=2):
    """{metrics, findings, errors}. Schema errors stop the analysis: metrics and findings are then empty."""
    errors = validate(topology)
    if errors:
        return {"metrics": {}, "findings": [], "errors": errors}
    t = topology
    nodes = {n["id"]: n for n in t["nodes"]}
    edges = [(e["id"], e["a"], e["b"]) for e in t["edges"]]
    ids = list(nodes)
    metrics = {"name": t["meta"]["name"], "nodes": len(ids), "edges": sum(a != b for _, a, b in edges)}
    metrics.update(graph_metrics(ids, edges, seed=seed, runs=runs))
    component_of = {v: i for i, comp in enumerate(components(ids, edges)) for v in comp}
    pairs, shared_fate, findings = resilience(t, nodes, edges, min_connectivity)
    metrics["shared_fate"] = shared_fate
    metrics["critical_pairs"] = pairs
    metrics["addresses"], more = address_checks(t, nodes, component_of)
    findings += more
    metrics["flows"], more = flow_checks(t, nodes)
    findings += more
    findings.sort(key=lambda f: (SEVERITIES.index(f["severity"]), f["id"]))
    metrics["findings"] = dict(collections.Counter(f["severity"] for f in findings))
    return {"metrics": metrics, "findings": findings, "errors": []}


def _cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def render_md(result):
    m = result["metrics"]
    if result["errors"]:
        return "# Network graph analysis — schema errors\n\n" + "\n".join(f"- {e}" for e in result["errors"]) + "\n"
    deg, rob = m["degree"], m["robustness"]
    out = [f"# Network graph analysis — {m['name']}", "",
           f"{m['nodes']} nodes · {m['edges']} edges · {m['components']} component(s), the largest "
           f"holding {m['largest_component_fraction']:.0%} of nodes.", "",
           f"- **Articulation points (G4):** {', '.join(m['articulation_points']) or 'none'}",
           f"- **Bridges (G4):** {', '.join(m['bridges']) or 'none'}",
           f"- **Hub concentration:** {m['hub_concentration']:.0%} of edge endpoints sit on the top "
           f"{len(deg['hub_nodes'])} node(s) ({', '.join(deg['hub_nodes'])}); max degree {deg['max']}, "
           f"mean {deg['mean']}",
           f"- **Highest betweenness (G6):** " + (", ".join(f"{v} {b}" for v, b in list(m['betweenness'].items())[:5])
                                                  or "none"),
           f"- **Shared-fate groups:** " + ("; ".join(f"{g} ({', '.join(ms)})" for g, ms in m["shared_fate"].items())
                                            or "none"), "", "## Critical pairs (G5)", ""]
    if m["critical_pairs"]:
        out += ["| Pair | Why | Node conn. | Edge conn. | Minimum cut | Single points | Bridges |",
                "|---|---|---|---|---|---|---|"]
        out += [f"| {_cell(p['from'])} → {_cell(p['to'])} | {_cell(p['why'])} | {p['node_connectivity']} | "
                f"{p['edge_connectivity']} | {', '.join(p['cut_set']) or '—'} | {', '.join(p['single_points']) or '—'} | "
                f"{', '.join(p['bridges']) or '—'} |"
                for p in m["critical_pairs"]]
    else:
        out.append("No critical pairs are declared, so resilience cannot be graded.")
    out += ["", "## Robustness (G9) — largest-component fraction", "",
            f"| Removed | Random (mean of {rob['runs']}, seed {rob['seed']}) | Highest degree first | "
            "Highest betweenness first |", "|---|---|---|---|"]
    out += [f"| {f:.0%} | {r} | {d} | {b} |"
            for f, r, d, b in zip(rob["fractions"], rob["random"], rob["degree"], rob["betweenness"])]
    nets = m["addresses"]["networks"]
    if nets:
        out += ["", "## Addresses (§3)", "", "| Network | CIDR | Class |", "|---|---|---|"]
        out += [f"| {_cell(i)} | {n['cidr']} | {n['class']} |" for i, n in nets.items()]
    out += ["", "## Findings", ""]
    if result["findings"]:
        out += ["| ID | Object | Confidence | Theory | Severity | Evidence | Summary |", "|---|---|---|---|---|---|---|"]
        out += [f"| {_cell(f['id'])} | {_cell(f['object'])} | {CONFIDENCE_MARK[f['confidence']]} {f['confidence']} | "
                f"{f['theory']} | {f['severity']} | {_cell(f['evidence'])} | {_cell(f['summary'])} |"
                for f in result["findings"]]
    else:
        out.append("None.")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="graph metrics, address and flow checks for a topology.json")
    a.add_argument("topology")
    fmt = a.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true", help="{metrics, findings, errors} as JSON")
    fmt.add_argument("--md", action="store_true", help="a Markdown report (the default)")
    a.add_argument("--seed", type=int, default=0, help="seed for random-failure removal")
    a.add_argument("--runs", type=int, default=20, help="random-failure runs to average")
    a.add_argument("--min-connectivity", type=int, default=2, help="target connectivity for critical pairs")
    args = ap.parse_args(argv)
    if args.runs < 1 or args.min_connectivity < 1:
        print("error: --runs and --min-connectivity must be at least 1", file=sys.stderr)
        return EXIT_USAGE
    path = pathlib.Path(args.topology)
    if not path.is_file():
        print(f"error: {path}: no such file", file=sys.stderr)
        return EXIT_USAGE
    try:
        topology = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        result = {"metrics": {}, "findings": [], "errors": [f"topology: not valid JSON ({e})"]}
    else:
        result = analyze(topology, seed=args.seed, runs=args.runs, min_connectivity=args.min_connectivity)
    sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n" if args.json else render_md(result))
    return EXIT_ERROR if result["errors"] else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
