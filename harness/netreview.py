#!/usr/bin/env python3
"""Audit a network estate from its evidence, and propose changes only where they're owed.

    python3 harness/netreview.py --evidence prod=infra/ --evidence branch=configs/branch/ --out review/
    python3 harness/netreview.py --evidence prod=infra/ --out review/ --audit-only
    python3 harness/netreview.py --evidence … --out review/ --intent migration     # always propose

    collect → redact → inventory → audit per network → topology.json → netgraph → score → [synthesis] → gate → propose
    files    secrets   counts per   netaudit, one     validated      graph,      scoring.md's  estate     per        netpropose, only
    only     masked    domain       read-only agent   in code        address,    formula, in   >1 net     network    for networks the
                       in code      each                             flow checks code                                 gate didn't pass

What code enforces, that the skills ask for in prose:
- **read-only, no live access**: evidence is files you name; the harness never connects to a device,
  controller or cloud API;
- **no secrets reach a model**: every evidence file is copied into --out/evidence/ with passwords, type-7
  keys, SNMP communities, pre-shared keys, private keys and secret-looking IaC values masked in place
  (line numbers preserved, so file:line evidence still points at the right line). Agents read only the
  redacted copies. Weak, default and committed secrets become findings without their values;
- **graph metrics by computation, not by eye**: the topology the agent recovers is validated, then
  netgraph.py computes articulation points, bridges, critical-pair connectivity, betweenness, address
  overlap and flow exposure, and its findings join the agent's;
- **score by formula**: agents report per-criterion counts; the harness computes p, points, base, the
  Critical (2.0) / High (6.0) caps and the weighted means, and writes the arithmetic beside every number;
- **the gate**: a network gets no proposal only when its capped score is ≥ --good-enough (9.0), no
  Critical/High is open, every declared critical pair has node connectivity ≥ --min-connectivity (2) —
  a network with none declared fails, its resilience is unassessed — its 🔬 flags are at most
  --max-flag-ratio of its objects, and it is neither decommissioned nor a duplicate. --intent migration
  proposes for every network. The decision is written down either way.

Exit status: 0 done · 1 error · 2 usage. Outputs land in --out: evidence/, audit/, gate.md, proposal/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import loop  # noqa: E402
import dbreview as DB  # noqa: E402  — the scoring formula is shared with the database family
import netgraph  # noqa: E402

EXIT_OK, EXIT_ERROR, EXIT_USAGE = 0, 1, 2
RUBRIC = "v1.0"
DOMAINS = ("addressing", "segmentation", "routing", "services", "resilience", "security")
SKIP_DIRS = {".git", ".terraform", "node_modules", "__pycache__", ".venv"}
MAX_BYTES = 2_000_000

# Object signals per domain — inventory weights and a sanity check on the agent's counts.
OBJECT_RE = {
    "addressing": r'resource\s+"(?:azurerm_(?:virtual_network|subnet)|aws_(?:vpc|subnet)|google_compute_(?:network|subnetwork))"'
                  r'|"type":\s*"Microsoft\.Network/virtualNetworks(?:/subnets)?"|^\s*ip(?:v6)? address \S',
    "segmentation": r'resource\s+"(?:azurerm_network_security_rule|aws_security_group_rule|aws_network_acl_rule|google_compute_firewall)"'
                    r'|^\s*security_rule\s*\{|^\s*(?:ingress|egress)\s*\{|^\s*(?:\d+\s+)?(?:permit|deny)\s'
                    r'|^\s*kind:\s*NetworkPolicy|^\s*set policy|^\s*edit \d+\s*$',
    "routing": r'resource\s+"(?:azurerm_route|azurerm_virtual_network_peering|aws_route|aws_vpc_peering_connection|google_compute_route)"'
               r'|^\s*router (?:ospf|bgp|eigrp|isis)|^\s*neighbor \S+ remote-as|^\s*ip route ',
    "services": r'resource\s+"(?:azurerm_(?:lb|nat_gateway|private_endpoint|private_dns_zone|virtual_network_gateway|firewall|application_gateway|dns_\w+)'
                r'|aws_(?:lb|nat_gateway|vpn_gateway|route53_\w+)|google_compute_router_nat)"|^\s*ip dhcp pool|^\s*ip name-server',
    "security": r'^\s*line vty|^\s*snmp-server |^\s*crypto (?:isakmp|ikev2|ipsec)|resource\s+"azurerm_virtual_network_gateway_connection"'
                r'|^\s*hostname \S|^\s*ntp server|^\s*logging (?:host|server)',
}

# ------------------------------------------------------------------ secrets

DEFAULT_SECRETS = {"public", "private", "cisco", "admin", "password", "changeme", "secret"}
SECRET_RULES = [  # (kind, regex with the secret in group "v", weakness or None)
    ("type-7 password", re.compile(r"(?P<k>\bpassword 7 )(?P<v>[0-9A-Fa-f]+)"), "reversible encoding"),
    ("cleartext password", re.compile(r"(?P<k>\b(?:password|secret) 0 )(?P<v>\S+)"), "cleartext"),
    ("enable secret", re.compile(r"(?P<k>\benable (?:secret|password)(?: \d)? )(?P<v>\S+)"), None),
    ("local account secret", re.compile(r"(?P<k>^\s*username \S+(?: privilege \d+)? (?:secret|password)(?: [0-9]+)? )(?P<v>\S+)", re.M), None),
    ("SNMP community", re.compile(r"(?P<k>\bsnmp-server community )(?P<v>\S+)"), "SNMPv1/v2c"),
    ("SNMP community", re.compile(r"(?P<k>\bset snmp community \"?)(?P<v>[^\"\s]+)"), "SNMPv1/v2c"),
    ("IKE pre-shared key", re.compile(r"(?P<k>\bcrypto isakmp key (?:\d )?)(?P<v>\S+)"), None),
    ("pre-shared key", re.compile(r"(?P<k>\bpre-shared-key (?:ascii-text |local |remote |key-string )?\"?)(?P<v>[^\"\s]+)"), None),
    ("key string", re.compile(r"(?P<k>\bkey-string (?:\d )?)(?P<v>\S+)"), None),
    ("routing auth key", re.compile(r"(?P<k>\b(?:message-digest-key \d+ md5|authentication-key|ip ospf authentication-key) (?:\d )?)(?P<v>\S+)"), None),
    ("FortiOS secret", re.compile(r"(?P<k>\bset (?:psksecret|password|passwd) ENC )(?P<v>\S+)"), None),
    ("IaC secret value", re.compile(r"(?P<k>\b(?:shared_key|admin_password|pre_shared_key|client_secret|password|secret|token|psk)"
                                    r"\s*[=:]\s*\")(?P<v>[^\"$\s{][^\"]*)", re.I), None),
]
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)


def redact(text, relname):
    """(masked text, [secret findings]). Line count is preserved; values never leave this function."""
    found = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        for kind, rx, weakness in SECRET_RULES:
            def sub(m, kind=kind, weakness=weakness):
                value = m.group("v")
                if value.startswith("<redacted"):
                    return m.group(0)
                weak = weakness
                if value.strip("\"'").casefold() in DEFAULT_SECRETS:
                    weak = f"default value{' (' + weakness + ')' if weakness else ''}"
                found.append({"kind": kind, "line": i + 1, "weakness": weak})
                return m.group("k") + f"<redacted:{kind.replace(' ', '-')}>"
            line = rx.sub(sub, line)
        lines[i] = line
    masked = "\n".join(lines)

    def pk(m):
        start = masked.count("\n", 0, m.start()) + 1
        found.append({"kind": "private key", "line": start, "weakness": None})
        return "\n".join("<redacted:private-key>" for _ in m.group(0).split("\n"))
    masked = PRIVATE_KEY.sub(pk, masked)
    findings = []
    for n, s in enumerate(found, 1):
        weak = s["weakness"]
        findings.append({
            "id": f"SEC-{pathlib.Path(relname).stem}-{s['line']}-{n}", "object": f"{relname}:{s['line']}",
            "severity": "High", "confidence": "decidable",
            "theory": "theory §11, §14 — authentication; secrets committed to evidence",
            "evidence": f"{relname}:{s['line']}",
            "summary": f"{s['kind']} present in the evidence" + (f" — {weak}" if weak else "") + " (value redacted)",
        })
    return masked, findings


def is_text(path):
    try:
        if path.stat().st_size > MAX_BYTES:
            return False
        return b"\0" not in path.read_bytes()[:4096]
    except OSError:
        return False


def collect(args):
    """{network: (root, [evidence files])} from --evidence name=path."""
    nets = {}
    for spec in args.evidence or []:
        name, _, path = spec.rpartition("=") if "=" in spec else ("", "", spec)
        path = pathlib.Path(path).resolve()
        if not path.exists():
            raise Usage(f"{path} does not exist")
        name = name or (path.stem if path.is_file() else path.name)
        if path.is_dir():
            files = sorted(f for f in path.rglob("*")
                           if f.is_file() and not (set(f.relative_to(path).parts) & SKIP_DIRS) and is_text(f))
            root = path
        else:
            files, root = [path], path.parent
        if not files:
            raise Usage(f"no readable text evidence under {path}")
        nets[name] = (root, files)
    if not nets:
        raise Usage("nothing to audit — pass --evidence name=path")
    return nets


def stage_evidence(nets, out):
    """Write redacted copies under out/evidence/<net>/ and return ({net: [copies]}, {net: [secret findings]})."""
    copies, secrets = {}, {}
    for name, (root, files) in nets.items():
        dest_root = out / "evidence" / name
        copies[name], secrets[name] = [], []
        for f in files:
            rel = f.relative_to(root)
            masked, found = redact(f.read_text(errors="replace"), str(rel))
            dest = dest_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(masked)
            copies[name].append(dest)
            secrets[name] += found
    return copies, secrets


def inventory(files):
    counts = {k: 0 for k in OBJECT_RE}
    for f in files:
        text = f.read_text(errors="replace")
        for k, pat in OBJECT_RE.items():
            counts[k] += len(re.findall(pat, text, re.I | re.M))
    return counts


class Usage(Exception):
    pass


# ------------------------------------------------------------------ schemas

S, I, B = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}
obj, ARR = loop._obj, (lambda item: {"type": "array", "items": item})
FINDING = obj({"id": S, "object": S, "severity": {"type": "string", "enum": ["Critical", "High", "Medium", "Low"]},
               "confidence": {"type": "string", "enum": ["decidable", "proxy", "needs-data"]},
               "theory": S, "evidence": S, "summary": S})
AUDIT_SCHEMA = obj({
    "usage_status": {"type": "string", "enum": ["in-use", "barely-used", "decommissioned", "duplicate", "unknown"]},
    "summary_md": S,
    "topology_json": S,
    "domains": ARR(obj({
        "domain": {"type": "string", "enum": list(DOMAINS)}, "coverage": S, "objects": I, "evaluation_md": S,
        "criteria": ARR(obj({"rubric": S, "criterion": S, "in_scope": I, "satisfied": I, "proxy_only": B})),
        "findings": ARR(FINDING),
    })),
})
SYNTH_SCHEMA = obj({"markdown": S, "coupling": ARR(obj({"from": S, "to": S, "via": S, "count": I}))})
PROPOSE_SCHEMA = obj({"files": ARR(obj({"name": S, "markdown": S}))})

AUDIT_PROMPT = """HARNESS-STAGE: net-audit · HARNESS-ITERATION: 1

Audit the **{net}** network with the netaudit skill (`{skill}`) and its reference docs in that folder \
(scoring.md, theory.md, graph-theory.md, topology-modeling.md, audit-lenses.md, the six domain rubrics, \
detection-signals.md). Read-only: never connect to anything and never change a file. The user is not available.

The evidence below is a **redacted copy**: secrets are masked as `<redacted:kind>` with line numbers kept, \
so cite `file:line` against these copies. Never try to recover a masked value. The harness has already \
recorded every masked secret as a security finding — do not report those again.

Evidence for {net} (relative to your working directory):
{files}
Object signals the harness counted per domain: {counts}

Return:
- `topology_json`: the recovered model as one JSON document following topology-modeling.md M1 exactly \
(meta, nodes, edges, networks, zones, flows, critical_pairs), with `file:line` evidence or `inferred: <reason>` \
for every element, and every network also present as a node with the same id. Declare the critical pairs; \
if the evidence doesn't say, infer them and mark the inference. **Do not compute graph metrics, overlaps or \
flow exposure** — the harness computes articulation points, bridges, connectivity, betweenness, CIDR \
overlap/containment, any-any rules, internet-to-management exposure and missing default-deny from this model, \
and adds those findings itself. Don't report them.
- `domains`: one entry per domain the evidence touches (addressing, segmentation, routing, services, resilience, \
security), each with `objects` (in-scope count), `criteria` (for each checklist criterion of that rubric: how many \
objects are **in scope** and how many **satisfy** it, and `proxy_only` when every failure is a ⚠️ proxy — **do not \
compute a score**), `findings` (severity, confidence — a runtime claim is always needs-data — theory section, \
file:line evidence), `evaluation_md` (scoring.md's template **without** the score line) and `coverage`.
- `usage_status` (unknown unless the evidence or the user says) and `summary_md` (the summary without the score): \
what is good, what is bad, what could improve.
"""

SYNTH_PROMPT = """HARNESS-STAGE: net-synthesis · HARNESS-ITERATION: 1

Write the estate synthesis (`estate-analysis.md`, per netaudit's Step 4, `{skill}`) from these per-network \
summaries and the harness-computed scores and graph results. Don't recompute any score or metric. Return the \
coupling edge list — which network reaches which, through what (peering, VPN, shared firewall, shared DNS, transit), \
and how many such links — plus cross-cutting patterns, the worst offenders and the 🔬 tally.

Nodes the harness found in more than one network's topology (shared dependencies): {shared}

{summaries}
"""

PROPOSE_PROMPT = """HARNESS-STAGE: net-propose · HARNESS-ITERATION: 1

Run netpropose (`{skill}`, with proposal.md) for **{nets}** only — the gate found the other networks good enough \
to leave alone ({skipped}). Intent: **{intent}**. The audit is in `{audit}` (per-domain evaluations, summary.md, \
topology.json and graph.json per network; scores.json; estate-analysis.md when present). Every decision cites the \
score and the finding that set it, and findings beat scores. No target design or diagrams exist in this run: say \
so, scope the proposal to decisions and sequencing, and do not claim diagram review. Return the proposal as files \
(name + markdown). Never write IaC. The user is not available.
"""


# ------------------------------------------------------------------ topology

def parse_topology(raw):
    """(topology, problems)."""
    try:
        topo = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        return None, [f"topology_json is not valid JSON: {e}"]
    if not isinstance(topo, dict):
        return None, ["topology_json must be a JSON object"]
    return topo, [f"topology: {p}" for p in netgraph.validate(topo)]


def check_audit(out):
    problems = []
    _, tp = parse_topology(out.get("topology_json"))
    problems += tp
    seen = [d["domain"] for d in out.get("domains", [])]
    if len(seen) != len(set(seen)):
        problems.append("each domain must appear once in `domains`")
    for d in out.get("domains", []):
        for c in d["criteria"]:
            if c["satisfied"] > c["in_scope"] or c["in_scope"] < 0:
                problems.append(f"{d['domain']} / {c['criterion']}: satisfied must be between 0 and in_scope")
    return problems


def domain_of(finding):
    """Which domain a harness finding belongs to: by id keyword first, then by theory section."""
    key = f"{finding['id']} {finding.get('theory', '')}".upper()
    if re.search(r"SPOF|BRIDGE|ARTIC|CONN|ROBUST|HUB|SHARED", key):
        return "resilience"
    if re.search(r"CIDR|OVERLAP|PARENT|DUP|PUBLIC|ADDR|PREFIX", key):
        return "addressing"
    if re.search(r"FLOW|MGMT|ANY|DENY|EXPOS|ZONE", key):
        return "segmentation"
    if re.search(r"§3|§4", key):
        return "addressing"
    if re.search(r"§11|§12", key):
        return "segmentation"
    return "resilience"


# ------------------------------------------------------------------ scoring (scoring.md v1.0, dbreview's formula)

def score_network(result, graph_findings, secret_findings, counts):
    by_domain = {d["domain"]: {**d, "findings": list(d["findings"])} for d in result["domains"]}
    extra = [(domain_of(f), f) for f in graph_findings] + [("security", f) for f in secret_findings]
    for dom, f in extra:
        by_domain.setdefault(dom, {"domain": dom, "coverage": "harness-computed findings only",
                                   "objects": counts.get(dom, 0), "evaluation_md": f"# {dom}\n",
                                   "criteria": [], "findings": []})["findings"].append(f)
    domains = []
    for dom in DOMAINS:
        if dom not in by_domain:
            continue
        d = by_domain[dom]
        s = DB.score_file(d)
        domains.append({**d, **s, "weight": max(1, d.get("objects") or counts.get(dom, 0) or 0)})
    findings = [x for d in domains for x in d["findings"]]
    uncapped = DB.weighted([(d["score"], d["weight"]) for d in domains])
    cap, by = DB.caps_for(findings)
    scored = [x for x in findings if x["confidence"] != "needs-data"]
    return {
        "domains": domains, "uncapped": uncapped, "cap": cap, "capped_by": by,
        "score": round(min(uncapped, cap), 1), "objects": sum(d["weight"] for d in domains),
        "critical": sum(1 for x in scored if x["severity"] == "Critical"),
        "high": sum(1 for x in scored if x["severity"] == "High"),
        "flags": sum(1 for x in findings if x["confidence"] == "needs-data"),
        "usage": result["usage_status"],
    }


def arithmetic(s):
    rows = "\n".join(f"| {g['rubric']} — {g['criterion']} | {g['satisfied']}/{g['in_scope']} | {g['p']:.2f} | "
                     f"{'🟢' if g['points'] == 2 else '🟡' if g['points'] == 1 else '🔴'} {g['points']} |"
                     for g in s["graded"]) or "| (no criteria reported — harness findings only) | | | |"
    cap = DB.cap_text(s["cap"], s["capped_by"], s["base"])
    return (f"\n\n## Score (computed by the harness, rubric {RUBRIC})\n\n| Criterion | Satisfied | p | Grade |\n"
            f"|---|---|---|---|\n{rows}\n\n**Base** {s['base']} · **{cap}** · **Domain score: {s['score']}** — "
            f"{DB.band(s['score'])}\n")


def findings_table(findings):
    if not findings:
        return ""
    rows = "\n".join(f"| {f['id']} | {f['object']} | {f['severity']} | {f['confidence']} | {f['theory']} | "
                     f"{f['evidence']} | {f['summary']} |" for f in findings)
    return ("\n\n## Findings computed by the harness\n\n| ID | Object | Severity | Conf. | Theory | Evidence | Summary |\n"
            f"|---|---|---|---|---|---|---|\n{rows}\n")


def graph_summary(metrics, min_conn):
    if not metrics:
        return "\n\n## Graph summary (harness)\n\nNot computed — the topology did not validate.\n"
    pairs = metrics.get("critical_pairs") or []
    rows = "\n".join(f"| {p.get('from')} → {p.get('to')} | {p.get('node_connectivity')} | {p.get('edge_connectivity')} | "
                     f"{', '.join(map(str, p.get('cut_set') or [])) or '—'} |" for p in pairs) or "| none declared | | | |"
    top = sorted((metrics.get("betweenness") or {}).items(), key=lambda kv: -kv[1])[:5]
    return ("\n\n## Graph summary (harness, graph-theory G3–G9)\n\n"
            f"Components **{metrics.get('components', '?')}** · articulation points "
            f"**{', '.join(metrics.get('articulation_points') or []) or 'none'}** · bridges "
            f"**{', '.join(metrics.get('bridges') or []) or 'none'}** · hub concentration "
            f"**{metrics.get('hub_concentration', '?')}**\n\n"
            f"| Critical pair | Node κ | Edge κ | Cut set |\n|---|---|---|---|\n{rows}\n\n"
            f"Gate threshold: node κ ≥ {min_conn}. Top betweenness: "
            + (", ".join(f"{n} {v:.2f}" for n, v in top) or "—") + "\n")


# ------------------------------------------------------------------ the gate

def gate(name, d, a):
    """(skip_proposal, reasons). Every reason is written down whichever way it goes."""
    if a.intent == "migration":
        return False, ["intent is migration — every network needs a proposal"]
    reasons, ok = [], True
    if d["score"] < a.good_enough:
        ok = False
        reasons.append(f"score {d['score']} is below {a.good_enough} ({DB.band(d['score'])})")
    if d["critical"] or d["high"]:
        ok = False
        reasons.append(f"{d['critical']} Critical / {d['high']} High finding(s) open")
    pairs = d.get("critical_pairs")
    if pairs is None:
        ok = False
        reasons.append("critical-pair connectivity was not computed — the topology did not validate")
    elif not pairs:
        ok = False
        reasons.append("no critical pairs declared — resilience is unassessed")
    else:
        weak = [f"{p.get('from')}→{p.get('to')} κ={p.get('node_connectivity')}" for p in pairs
                if (p.get("node_connectivity") or 0) < a.min_connectivity]
        if weak:
            ok = False
            reasons.append(f"critical pair(s) below node connectivity {a.min_connectivity}: {', '.join(weak)}")
    if d["usage"] in ("decommissioned", "duplicate"):
        ok = False
        reasons.append(f"usage is {d['usage']} — a retirement verdict is itself a proposal")
    if d["flags"] > a.max_flag_ratio * max(1, d["objects"]):
        ok = False
        reasons.append(f"{d['flags']} 🔬 flags on {d['objects']} objects — a high score riding on unverified "
                       "claims is not a clean bill of health")
    if ok:
        reasons.append(f"score {d['score']} ≥ {a.good_enough}, no Critical/High, every critical pair κ ≥ "
                       f"{a.min_connectivity}, usage {d['usage']}, {d['flags']} 🔬 flag(s) — good enough: keep")
    return ok, reasons


# ------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--evidence", action="append", help="[name=]path — a file or folder of evidence, one network each")
    ap.add_argument("--out", required=True, help="where the redacted evidence, audit, gate decision and proposal go")
    ap.add_argument("--intent", choices=["remediation", "migration"], default="remediation")
    ap.add_argument("--good-enough", type=float, default=9.0, help="capped score at which no proposal is made")
    ap.add_argument("--max-flag-ratio", type=float, default=0.10)
    ap.add_argument("--min-connectivity", type=int, default=2, help="node connectivity every critical pair needs")
    ap.add_argument("--audit-only", action="store_true", help="stop after the gate")
    ap.add_argument("--skills", default=str(HERE.parent / "skills"))
    ap.add_argument("--model")
    ap.add_argument("--delegate-model")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--budget-usd", type=float)
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args(argv)

    out = pathlib.Path(a.out).resolve()
    run_dir = out / "runs" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    ctx = loop.Ctx(repo=out, skills=pathlib.Path(a.skills).resolve(), test_cmd="", base="HEAD", cap=1,
                   model=a.model, delegate_model=a.delegate_model, concurrency=a.concurrency, budget=a.budget_usd,
                   timeout=a.timeout, dry=False, run_dir=run_dir, claude_bin=os.environ.get("HARNESS_CLAUDE", "claude"))
    try:
        nets = collect(a)
        copies, secrets = stage_evidence(nets, out)
        counts = {name: inventory(files) for name, files in copies.items()}
        (out / "inventory.json").write_text(json.dumps(counts, indent=2))
        for name, c in counts.items():
            loop.log(f"{name}: {len(copies[name])} file(s), {len(secrets[name])} secret(s) redacted · "
                     + " · ".join(f"{v} {k}" for k, v in c.items() if v))

        audit_skill = loop.skill_path(ctx, "netaudit")

        def job(name):
            root = out / "evidence" / name
            files = "".join(f"- `{f.relative_to(root)}`\n" for f in copies[name])
            prompt = AUDIT_PROMPT.format(net=name, skill=audit_skill, files=files, counts=json.dumps(counts[name]))
            # Read-only tools, working inside the redacted copy — never the original evidence.
            return lambda: loop.claude_checked(ctx, f"audit-{name}", prompt, AUDIT_SCHEMA, loop.READ_TOOLS, check_audit,
                                               model=a.delegate_model, cwd=root)

        results = loop.fan_out(ctx, [(name, job(name)) for name in copies])
        failed = {n: r for n, r in results.items() if isinstance(r, Exception)}
        if failed:
            raise loop.HarnessError("audit did not return for: " + "; ".join(f"{n} ({e})" for n, e in failed.items()))

        audit = out / "audit"
        scores, topologies = {}, {}
        for name, res in sorted(results.items()):
            topo, _ = parse_topology(res["topology_json"])
            graph = netgraph.analyze(topo, min_connectivity=a.min_connectivity)
            if graph.get("errors"):
                raise loop.HarnessError(f"{name}: topology failed validation: {'; '.join(graph['errors'][:5])}")
            topologies[name] = topo
            d = score_network(res, graph["findings"], secrets[name], counts[name])
            d["critical_pairs"] = (graph.get("metrics") or {}).get("critical_pairs")
            scores[name] = d
            ndir = audit / name
            ndir.mkdir(parents=True, exist_ok=True)
            (ndir / "topology.json").write_text(json.dumps(topo, indent=2) + "\n")
            (ndir / "graph.json").write_text(json.dumps(graph, indent=2, default=str) + "\n")
            harness_ids = {f["id"] for f in graph["findings"]} | {f["id"] for f in secrets[name]}
            for dom in d["domains"]:
                own = [f for f in dom["findings"] if f["id"] in harness_ids]
                (ndir / f"{dom['domain']}.md").write_text(
                    dom["evaluation_md"].rstrip() + findings_table(own) + arithmetic(dom)
                    + f"\n_Coverage: {dom['coverage']}_\n")
            cap = DB.cap_text(d["cap"], d["capped_by"], d["uncapped"])
            (ndir / "summary.md").write_text(
                res["summary_md"].rstrip() + graph_summary(graph.get("metrics"), a.min_connectivity)
                + f"\n## Score (harness, rubric {RUBRIC})\n\nObject-weighted mean of the domain scores **{d['uncapped']}** "
                f"· {cap} · **Network score: {d['score']} — {DB.band(d['score'])}** · {d['critical']} Critical · "
                f"{d['high']} High · {d['flags']} 🔬 flag(s) open · usage: {d['usage']}\n")
            loop.log(f"{name}: {d['score']} — {DB.band(d['score'])} ({cap}; {d['flags']} 🔬)")

        total = sum(d["objects"] for d in scores.values())
        estate_cap = min([d["cap"] for d in scores.values()] + [10.0])
        estate = {"uncapped": DB.weighted([(d["uncapped"], d["objects"]) for d in scores.values()]),
                  "score": round(min(DB.weighted([(d["score"], d["objects"]) for d in scores.values()]), estate_cap), 1),
                  "objects": total}
        if len(scores) > 1:
            ids = {n: {x["id"] for x in t.get("nodes", [])} for n, t in topologies.items()}
            shared = sorted({i for n in ids for i in ids[n] if sum(i in s for s in ids.values()) > 1})
            summaries = "\n\n".join(f"### {n} — {d['score']} ({DB.band(d['score'])})\n{(audit / n / 'summary.md').read_text()}"
                                    for n, d in scores.items())
            syn = loop.claude(ctx, "synthesis", SYNTH_PROMPT.format(skill=audit_skill, summaries=summaries,
                                                                    shared=", ".join(shared) or "none"),
                              SYNTH_SCHEMA, loop.READ_TOOLS)
            edges = "\n".join(f"- {e['from']} → {e['to']} via {e['via']} ({e['count']})" for e in syn["coupling"]) \
                or "- none found"
            (audit / "estate-analysis.md").write_text(
                syn["markdown"].rstrip() + f"\n\n## Estate score (harness)\n\nCapped **{estate['score']}** — "
                f"{DB.band(estate['score'])} · uncapped {estate['uncapped']} · {total} objects\n\n"
                f"## Coupling edges\n{edges}\n\n## Shared dependencies (harness)\n"
                + ("\n".join(f"- {s}" for s in shared) or "- none") + "\n")
        (audit / "scores.json").write_text(json.dumps({"rubric": RUBRIC, "estate": estate, "networks": {
            n: {k: v for k, v in d.items() if k != "domains"} for n, d in scores.items()}}, indent=2, default=str))

        decisions = {n: gate(n, d, a) for n, d in scores.items()}
        lines = [f"# Proposal gate — {dt.datetime.now(dt.timezone.utc):%Y-%m-%d}", "",
                 f"Intent **{a.intent}** · good enough at **{a.good_enough}** · critical pairs need node κ ≥ "
                 f"**{a.min_connectivity}** · at most **{a.max_flag_ratio:.0%}** 🔬 flags per object", "",
                 "| Network | Score | Proposal | Why |", "|---|---|---|---|"]
        for n, (skip, why) in decisions.items():
            lines.append(f"| {n} | {scores[n]['score']} | {'**no** — good enough' if skip else 'yes'} | {'; '.join(why)} |")
        (out / "gate.md").write_text("\n".join(lines) + "\n")
        todo = [n for n, (skip, _) in decisions.items() if not skip]
        skipped = [n for n, (skip, _) in decisions.items() if skip]
        (out / "gate-status.json").write_text(json.dumps({"requires_proposal": todo, "passed": skipped}, indent=2) + "\n")
        loop.log(f"gate: propose for {', '.join(todo) or 'nothing'}; leave alone {', '.join(skipped) or 'nothing'}")

        if todo and not a.audit_only:
            res = loop.claude(ctx, "propose", PROPOSE_PROMPT.format(
                skill=loop.skill_path(ctx, "netpropose"), nets=", ".join(todo), skipped=", ".join(skipped) or "none",
                intent=a.intent, audit=audit), PROPOSE_SCHEMA, loop.READ_TOOLS)
            pdir = out / "proposal"
            pdir.mkdir(parents=True, exist_ok=True)
            for f in res["files"]:
                name = re.sub(r"[^\w.-]+", "-", f["name"]).strip("-") or "proposal.md"
                (pdir / (name if name.endswith(".md") else name + ".md")).write_text(f["markdown"].rstrip() + "\n")
            loop.log(f"proposal: {len(res['files'])} file(s) in {pdir}")
        elif not todo:
            loop.log("no proposal: every network passed the gate — see gate.md")
        return EXIT_OK
    except Usage as e:
        loop.log(f"error: {e}")
        return EXIT_USAGE
    except loop.HarnessError as e:
        loop.log(f"error: {e}")
        return EXIT_ERROR
    finally:
        if ctx.cost:
            loop.log(f"spent ${ctx.cost:.2f} this run")


if __name__ == "__main__":
    sys.exit(main())
