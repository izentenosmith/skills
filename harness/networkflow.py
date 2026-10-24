#!/usr/bin/env python3
"""Coordinate the independent network skills for existing or new networks.

Examples:
  python3 harness/networkflow.py --mode existing --evidence prod=./infra --out ./review
  python3 harness/networkflow.py --mode new --requirements ./requirements.md --out ./proposal
  python3 harness/networkflow.py --mode new --requirements ./requirements.md --stages design,diagram --out ./work
  python3 harness/networkflow.py --mode new --stages blueprint --proposal-input ./work/proposal/proposal.md \
    --design-input ./work/design --proposal-accepted --out ./work

The existing-network audit and its quality gate are delegated to netreview.py. New and partial
workflows invoke the standalone skills and save their artifacts under --out. The blueprint (final
diagrams, network-design.md, accepted topology.json) is a separate run after explicit acceptance; no
stage ever writes IaC or touches a network.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import ipaddress
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import loop  # noqa: E402
import netgraph  # noqa: E402

EXIT_OK, EXIT_ERROR, EXIT_USAGE = 0, 1, 2
STAGES = ("audit", "design", "diagram", "propose", "blueprint")
FILES_SCHEMA = loop._obj({"files": {"type": "array", "items": loop._obj({"name": {"type": "string"},
                                                                           "content": {"type": "string"}})}})
VIEWS = {  # file name → required page name
    "logical-topology.drawio": "Logical topology (L3)",
    "segmentation.drawio": "Segmentation (zones and flows)",
    "physical-topology.drawio": "Physical topology (L1/L2)",
}
LEGEND = "network diagram conventions"
FREE_IDS = ("deco-", "flowgrp-")


class Usage(Exception):
    pass


def safe_name(s: str, fallback: str) -> str:
    return re.sub(r"[^\w.-]+", "-", s).strip("-.") or fallback


def read_text(path: pathlib.Path, label: str) -> str:
    if not path.exists() or not path.is_file():
        raise Usage(f"{label} artifact not found: {path}")
    return path.read_text(errors="replace")


def skill_call(ctx, stage: str, prompt: str, outdir: pathlib.Path, cwd: pathlib.Path):
    """Run a skill and save its declared artifacts. In a dry run, only the prompt is written."""
    result = loop.claude(ctx, stage, prompt, FILES_SCHEMA, loop.READ_TOOLS, cwd=cwd)
    if result is None:
        loop.log(f"{stage}: dry run — prompt written to {ctx.run_dir / 'calls'}")
        return []
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for item in result["files"]:
        name = safe_name(item["name"], f"{stage}.md")
        if stage in ("diagram", "blueprint") and name.endswith(".drawio"):
            if "<mxfile" not in item["content"] or "</mxfile>" not in item["content"]:
                raise loop.HarnessError(f"{stage} returned {name!r} without diagrams.net XML")
        path = outdir / name
        path.write_text(item["content"].rstrip() + "\n")
        written.append(path)
    if not written:
        raise loop.HarnessError(f"{stage} returned no artifacts")
    loop.log(f"{stage}: {len(written)} artifact(s) in {outdir}")
    return written


# ------------------------------------------------------------------ model and diagram checks

def load_topology(path: pathlib.Path, *, error_type=loop.HarnessError, status=None):
    try:
        topo = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise error_type(f"unreadable topology {path}: {e}")
    problems = netgraph.validate(topo)
    if problems:
        raise error_type(f"{path} failed validation: {'; '.join(problems[:5])}")
    if status and (topo.get("meta") or {}).get("status") != status:
        raise error_type(f"{path}: meta.status must be {status!r}")
    return topo


def model_ids(topo):
    ids = set()
    for key in ("nodes", "edges", "networks", "zones", "flows"):
        ids |= {x["id"] for x in topo.get(key) or [] if "id" in x}
    return ids


def strip_label(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", html.unescape(value or ""))


def validate_diagram_set(paths, topo=None, *, error_type=loop.HarnessError):
    """Require the canonical views, their page names and legend, and — with a model — IDs and CIDRs that agree."""
    by_name = {}
    for p in paths:
        name = p.name.casefold()
        if name not in VIEWS:
            raise error_type(f"diagram must be one of {', '.join(VIEWS)}: {p.name}")
        if name in by_name:
            raise error_type(f"duplicate diagram: {p.name}")
        by_name[name] = p
    required = ["logical-topology.drawio", "segmentation.drawio"]
    if topo and any(e.get("kind") == "l2-link" for e in topo.get("edges") or []):
        required.append("physical-topology.drawio")      # on-prem L2 evidence exists, so the physical view is owed
    missing = [r for r in required if r not in by_name]
    if missing:
        raise error_type(f"missing required diagram(s): {', '.join(missing)}")

    ids = model_ids(topo) if topo else None
    cidrs = {n["id"]: n["cidr"] for n in (topo or {}).get("networks") or []}
    for name, path in by_name.items():
        try:
            root = ET.fromstring(path.read_text(errors="replace"))
        except (ET.ParseError, OSError) as exc:
            raise error_type(f"invalid draw.io XML in {path}: {exc}")
        if root.tag.rsplit("}", 1)[-1] != "mxfile":
            raise error_type(f"{path.name} must have an mxfile root element")
        pages = [n for n in root.iter() if n.tag.rsplit("}", 1)[-1] == "diagram"]
        page = next((pg for pg in pages if pg.attrib.get("name", "").strip() == VIEWS[name]), None)
        if page is None:
            raise error_type(f"{path.name} needs a page named {VIEWS[name]!r}")
        cells = [c for c in page.iter() if c.tag.rsplit("}", 1)[-1] == "mxCell"]
        if not cells:
            raise error_type(f"{path.name}: page {VIEWS[name]!r} has no cells — save it uncompressed")
        labels = {c.attrib.get("id", ""): strip_label(c.attrib.get("value", "")) for c in cells}
        if not any(LEGEND in v.casefold() for v in labels.values()):
            raise error_type(f"{path.name}: page {VIEWS[name]!r} needs a visible legend naming 'Network diagram conventions'")
        if ids is None:
            continue
        edge_ids = {c.attrib.get("id") for c in cells if c.attrib.get("edge") == "1"}
        for c in cells:
            cid, parent = c.attrib.get("id", ""), c.attrib.get("parent")
            if cid in ("0", "1") or cid.startswith(FREE_IDS) or parent in edge_ids:
                continue
            if cid not in ids:
                raise error_type(f"{path.name}: cell {cid!r} is not a topology.json id (prefix decorative cells 'deco-')")
        if name == "logical-topology.drawio":
            for nid, cidr in cidrs.items():
                if nid not in labels:
                    raise error_type(f"{path.name}: network {nid!r} is not drawn")
                found = re.findall(r"[0-9A-Fa-f:.]+/\d{1,3}", labels[nid])
                if not any(_same_net(f, cidr) for f in found):
                    raise error_type(f"{path.name}: network {nid!r} must be labelled with its CIDR {cidr}")
            for pair in topo.get("critical_pairs") or []:
                for end in (pair.get("from"), pair.get("to")):
                    if end in {n["id"] for n in topo.get("nodes") or []} and end not in labels:
                        raise error_type(f"{path.name}: critical-pair endpoint {end!r} is not drawn")
        if name == "segmentation.drawio":
            for z in topo.get("zones") or []:
                if z["id"] not in labels:
                    raise error_type(f"{path.name}: zone {z['id']!r} is not drawn")
    return [by_name[n] for n in VIEWS if n in by_name]


def _same_net(a, b):
    try:
        return ipaddress.ip_network(a, strict=False) == ipaddress.ip_network(b, strict=False)
    except ValueError:
        return False


def design_artifacts(path: pathlib.Path, *, error_type=Usage):
    """(design.md text, topology.json path) from a design folder, or a design.md with topology.json beside it."""
    folder = path if path.is_dir() else path.parent
    md = path if path.is_file() else folder / "design.md"
    topo = folder / "topology.json"
    return read_text(md, "design"), (topo if topo.exists() else None)


# ------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--mode", choices=("existing", "new"), required=True)
    ap.add_argument("--evidence", action="append", help="[name=]path of network evidence (existing networks)")
    ap.add_argument("--requirements", help="requirements document (new networks)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--audit-input", help="an audit folder produced elsewhere (netreview's audit/)")
    ap.add_argument("--design-input", help="a design folder (design.md + topology.json) or design.md")
    ap.add_argument("--diagram-input", action="append", help="draw.io diagram input; repeat once per view")
    ap.add_argument("--proposal-input", help="proposal.md for the blueprint stage")
    ap.add_argument("--proposal-accepted", action="store_true", help="confirm that the supplied proposal was accepted")
    ap.add_argument("--stages", help="comma-separated ordered subset of: " + ",".join(STAGES))
    ap.add_argument("--intent", choices=("remediation", "migration"), default="remediation")
    ap.add_argument("--good-enough", type=float, default=9.0)
    ap.add_argument("--max-flag-ratio", type=float, default=0.10)
    ap.add_argument("--min-connectivity", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true", help="write each stage's prompt and call nothing")
    ap.add_argument("--skills", default=str(HERE.parent / "skills"))
    ap.add_argument("--model")
    ap.add_argument("--delegate-model")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--budget-usd", type=float)
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args(argv)

    out = pathlib.Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    skills = pathlib.Path(a.skills).resolve()
    try:
        if a.stages:
            stages = [x.strip() for x in a.stages.split(",") if x.strip()]
            if not stages or any(s not in STAGES for s in stages) or len(set(stages)) != len(stages):
                raise Usage("--stages must be a comma-separated, non-repeating subset of " + ", ".join(STAGES))
            positions = [STAGES.index(s) for s in stages]
            if positions != sorted(positions):
                raise Usage("--stages must follow workflow order: " + ", ".join(STAGES))
        else:
            stages = ["audit", "design", "diagram", "propose"] if a.mode == "existing" else ["design", "diagram", "propose"]
        if a.mode == "new" and "audit" in stages:
            raise Usage("a new-network workflow has no audit stage")
        if "blueprint" in stages and stages != ["blueprint"]:
            raise Usage("blueprint is a standalone final stage: run design/diagram/propose, accept, then run blueprint")
        if "blueprint" in stages and (not a.proposal_input or not a.proposal_accepted):
            raise Usage("blueprint requires --proposal-input and explicit --proposal-accepted")
        if "blueprint" in stages and not a.design_input:
            raise Usage("blueprint requires --design-input for the design the accepted proposal refers to")
        if "audit" in stages and not a.evidence and not a.dry_run:
            raise Usage("existing-network audit requires --evidence")
        if a.mode == "new" and "design" in stages and not a.requirements:
            raise Usage("new-network design requires --requirements")

        run_dir = out / "runs" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        ctx = loop.Ctx(repo=out, skills=skills, test_cmd="", base="HEAD", cap=1, model=a.model,
                       delegate_model=a.delegate_model, concurrency=a.concurrency, budget=a.budget_usd,
                       timeout=a.timeout, dry=a.dry_run, run_dir=run_dir,
                       claude_bin=os.environ.get("HARNESS_CLAUDE", "claude"))
        for name in ("netaudit", "netdesign", "netdiagram", "netpropose", "netblueprint"):
            loop.skill_path(ctx, name)                       # fail early when a skill is missing

        audit_path = pathlib.Path(a.audit_input).resolve() if a.audit_input else out / "audit"
        if "audit" in stages and not a.dry_run:
            cmd = [sys.executable, str(HERE / "netreview.py"), "--out", str(out / "audit-run"), "--intent", a.intent,
                   "--good-enough", str(a.good_enough), "--max-flag-ratio", str(a.max_flag_ratio),
                   "--min-connectivity", str(a.min_connectivity), "--skills", str(skills), "--audit-only",
                   "--concurrency", str(a.concurrency), "--timeout", str(a.timeout)]
            for spec in a.evidence:
                cmd += ["--evidence", spec]
            for flag, val in (("--model", a.model), ("--delegate-model", a.delegate_model),
                              ("--budget-usd", a.budget_usd)):
                if val is not None:
                    cmd += [flag, str(val)]
            if subprocess.run(cmd, check=False).returncode:
                raise loop.HarnessError("audit harness (netreview.py) failed — see its log above")
            shutil.copytree(out / "audit-run" / "audit", out / "audit", dirs_exist_ok=True)
            for f in ("gate.md", "gate-status.json"):
                shutil.copy2(out / "audit-run" / f, out / f)
            status = json.loads((out / "gate-status.json").read_text())
            if a.mode == "existing" and not a.stages and not status["requires_proposal"] and a.intent != "migration":
                (out / "workflow.json").write_text(json.dumps({
                    "mode": a.mode, "stages_requested": stages, "stages_completed": ["audit"], "status": "gate-passed",
                    "finished_at": dt.datetime.now(dt.timezone.utc).isoformat()}, indent=2) + "\n")
                loop.log("every network passed the score, risk and connectivity gates; no redesign required")
                return EXIT_OK

        audit_text = ""
        if a.mode == "existing" and any(s in stages for s in ("design", "propose")):
            if audit_path.is_dir():
                audit_text = "\n\n".join(p.read_text(errors="replace") for p in sorted(audit_path.glob("*/summary.md")))
            elif a.audit_input:
                audit_text = read_text(audit_path, "audit")
            if not audit_text and not a.dry_run:
                raise Usage("design/propose for an existing network needs the audit stage or --audit-input")

        design_dir = out / "design"
        design_text, topo_path = "", None
        if a.design_input:
            design_text, topo_path = design_artifacts(pathlib.Path(a.design_input).resolve())
        elif design_dir.exists():
            design_text, topo_path = design_artifacts(design_dir)

        if "design" in stages:
            req = read_text(pathlib.Path(a.requirements).resolve(), "requirements") if a.requirements else ""
            prompt = ("HARNESS-STAGE: nf-design · HARNESS-ITERATION: 1\n\n"
                      f"Run netdesign (`{loop.skill_path(ctx, 'netdesign')}`) for this {a.mode} network. Intent: {a.intent}.\n"
                      f"Requirements:\n{req or '(none supplied)'}\n\n"
                      f"Audit evidence folder: {audit_path if audit_text else '(none)'}\nAudit summaries:\n{audit_text or '(new network; no audit)'}\n\n"
                      "For an audited network, read each network's audit/<net>/topology.json and keep the IDs of surviving "
                      "elements. Return exactly two files: design.md (the reviewable design, with assumptions and open "
                      "questions explicit) and topology.json (the target model per topology-modeling.md, meta.stage "
                      "'design', meta.status 'proposed', critical pairs declared). Never write IaC.")
            files = skill_call(ctx, "design", prompt, design_dir, out)
            if files:
                names = {p.name for p in files}
                if names != {"design.md", "topology.json"}:
                    raise loop.HarnessError(f"design must return design.md and topology.json; got {sorted(names)}")
                topo = load_topology(design_dir / "topology.json")
                graph = netgraph.analyze(topo, min_connectivity=a.min_connectivity)
                (design_dir / "graph.json").write_text(json.dumps(graph, indent=2, default=str) + "\n")
                worst = [f for f in graph["findings"] if f["severity"] in ("Critical", "High")]
                if worst:
                    loop.log(f"design: netgraph reports {len(worst)} Critical/High finding(s) in the target — "
                             "see design/graph.json; the proposal must address or accept them")
                design_text, topo_path = design_artifacts(design_dir)
        elif any(s in stages for s in ("diagram", "propose", "blueprint")) and not design_text and not a.dry_run:
            raise Usage("diagram/propose/blueprint need a design: run the design stage or pass --design-input")

        topo = load_topology(topo_path, error_type=Usage) if topo_path else None
        diagram_paths = ([pathlib.Path(p).resolve() for p in a.diagram_input] if a.diagram_input
                         else sorted((out / "diagrams").glob("*.drawio")))
        if "diagram" in stages:
            prompt = ("HARNESS-STAGE: nf-diagram · HARNESS-ITERATION: 1\n\n"
                      f"Run netdiagram (`{loop.skill_path(ctx, 'netdiagram')}`) and follow diagram-conventions.md exactly. "
                      f"Draw the target model in `{topo_path}` (status proposed).\n\nDesign:\n{design_text}\n\n"
                      "Return logical-topology.drawio and segmentation.drawio, plus physical-topology.drawio when the model "
                      "has l2-link edges. Each must be a complete, uncompressed mxfile with the required page name, a visible "
                      "legend containing 'Network diagram conventions', cell IDs equal to topology.json IDs (decorative cells "
                      "prefixed 'deco-'), and every network labelled with its CIDR.")
            paths = skill_call(ctx, "diagram", prompt, out / "diagrams", out)
            if paths:
                diagram_paths = validate_diagram_set(paths, topo)
        elif any(s in stages for s in ("propose", "blueprint")) and not a.dry_run:
            diagram_paths = validate_diagram_set(diagram_paths, topo, error_type=Usage)

        if "propose" in stages:
            prompt = ("HARNESS-STAGE: nf-propose · HARNESS-ITERATION: 1\n\n"
                      f"Run netpropose (`{loop.skill_path(ctx, 'netpropose')}`) to prepare the reviewable recommendation. "
                      f"Intent: {a.intent}.\nAudit evidence folder: {audit_path if audit_text else '(new network; no audit)'}\n"
                      f"Audit summaries:\n{audit_text or '(new network; no audit)'}\n\nDesign:\n{design_text}\n\n"
                      f"Target topology: {topo_path}\nDiagrams:\n" + "\n".join(f"- {p}" for p in diagram_paths) + "\n\n"
                      "Cite audit finding IDs and file:line evidence. Confirm the diagrams follow diagram-conventions.md and "
                      "match the target topology; route any mismatch back rather than correcting it. Return proposal.md with "
                      "the decision register, cut-over sequence, validation, rollback and open questions. Do not apply changes "
                      "or write IaC. End by stating that acceptance is required before netblueprint runs.")
            skill_call(ctx, "propose", prompt, out / "proposal", out)

        if "blueprint" in stages:
            proposal_path = pathlib.Path(a.proposal_input).resolve()
            proposal_text = read_text(proposal_path, "accepted proposal")
            prompt = ("HARNESS-STAGE: nf-blueprint · HARNESS-ITERATION: 1\n\n"
                      f"Run netblueprint (`{loop.skill_path(ctx, 'netblueprint')}`). The user explicitly confirms acceptance of "
                      f"proposal `{proposal_path}`. The accepted proposal and the design are authoritative; if they conflict, "
                      f"stop and report it.\n\nAccepted proposal:\n{proposal_text}\n\nDesign:\n{design_text}\n\n"
                      f"Target topology: {topo_path}\nApproved diagrams:\n" + "\n".join(f"- {p}" for p in diagram_paths) + "\n\n"
                      "Return network-design.md (per blueprint.md), topology.json (meta.stage 'blueprint', meta.status "
                      "'accepted', IDs unchanged) and the final .drawio views per diagram-conventions.md. No IaC, no device "
                      "configuration, no secrets.")
            files = skill_call(ctx, "blueprint", prompt, out / "blueprint", out)
            if files:
                names = {p.name for p in files}
                for need in ("network-design.md", "topology.json"):
                    if need not in names:
                        raise loop.HarnessError(f"blueprint must return {need}")
                final = load_topology(out / "blueprint" / "topology.json", status="accepted")
                validate_diagram_set([p for p in files if p.suffix == ".drawio"], final)
                graph = netgraph.analyze(final, min_connectivity=a.min_connectivity)
                (out / "blueprint" / "graph.json").write_text(json.dumps(graph, indent=2, default=str) + "\n")
                open_worst = [f["id"] for f in graph["findings"] if f["severity"] in ("Critical", "High")]
                if open_worst:
                    loop.log(f"blueprint: {len(open_worst)} Critical/High finding(s) remain in the accepted model "
                             f"({', '.join(open_worst[:5])}) — network-design.md §3 must record their acceptance")

        (out / "workflow.json").write_text(json.dumps({
            "mode": a.mode, "stages_requested": stages, "stages_completed": [] if a.dry_run else stages,
            "dry_run": a.dry_run, "finished_at": dt.datetime.now(dt.timezone.utc).isoformat()}, indent=2) + "\n")
        return EXIT_OK
    except Usage as e:
        loop.log(f"usage error: {e}")
        return EXIT_USAGE
    except loop.HarnessError as e:
        loop.log(f"workflow error: {e}")
        return EXIT_ERROR
    finally:
        if "ctx" in locals() and ctx.cost:
            loop.log(f"spent ${ctx.cost:.2f} this run")


if __name__ == "__main__":
    sys.exit(main())
