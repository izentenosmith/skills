#!/usr/bin/env python3
"""Coordinate independent database skills for existing or new databases.

Examples:
  python3 harness/dbworkflow.py --mode existing --ddl shop=./db/shop --out ./review
  python3 harness/dbworkflow.py --mode new --requirements ./requirements.md --out ./proposal
  python3 harness/dbworkflow.py --mode new --requirements ./requirements.md --stages design,diagram --out ./work
  python3 harness/dbworkflow.py --mode new --stages build --proposal-input ./work/proposal/proposal.md \
    --design-input ./work/design/design.md --proposal-accepted --out ./work

The existing-database audit and its quality gate are delegated to dbreview.py. New and
partial workflows invoke the standalone skills and save their artifacts under --out.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import loop  # noqa: E402

EXIT_OK, EXIT_ERROR, EXIT_USAGE = 0, 1, 2
STAGES = ("audit", "design", "diagram", "propose", "build")
FILES_SCHEMA = loop._obj({"files": {"type": "array", "items": loop._obj({"name": {"type": "string"},
                                                                           "content": {"type": "string"}})}})


class Usage(Exception):
    pass


def safe_name(s: str, fallback: str) -> str:
    return re.sub(r"[^\w.-]+", "-", s).strip("-.") or fallback


def skill_call(ctx, stage: str, skill: str, prompt: str, outdir: pathlib.Path, cwd: pathlib.Path):
    """Run a skill and save its declared artifacts."""
    result = loop.claude(ctx, stage, prompt, FILES_SCHEMA, loop.READ_TOOLS, cwd=cwd)
    if stage == "diagram" and len(result["files"]) != 2:
        raise loop.HarnessError(f"diagram stage must return both required views; got {len(result['files'])} file(s)")
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for item in result["files"]:
        name = safe_name(item["name"], f"{stage}.md")
        path = outdir / name
        if stage == "diagram":
            if not name.endswith(".drawio"):
                raise loop.HarnessError(f"diagram stage returned {name!r}; expected native .drawio output")
            if "<mxfile" not in item["content"] or "</mxfile>" not in item["content"]:
                raise loop.HarnessError(f"diagram stage returned {name!r} without diagrams.net XML")
        if stage == "build" and not name.endswith(".sql"):
            raise loop.HarnessError(f"build stage returned {name!r}; expected a .sql artifact")
        path.write_text(item["content"].rstrip() + "\n")
        written.append(path)
    if not written:
        raise loop.HarnessError(f"{stage} returned no artifacts")
    loop.log(f"{stage}: {len(written)} artifact(s) in {outdir}")
    return written


def read_text(path: pathlib.Path, label: str) -> str:
    if not path.exists() or not path.is_file():
        raise Usage(f"{label} artifact not found: {path}")
    return path.read_text(errors="replace")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("existing", "new"), required=True)
    ap.add_argument("--out", required=True, help="workflow artifact directory")
    ap.add_argument("--ddl", action="append", help="existing database input, [name=]SQL file or folder; repeatable")
    ap.add_argument("--dsn-env", action="append", help="existing database: environment variable holding a read-only dump DSN")
    ap.add_argument("--requirements", help="new database requirements or domain description file")
    ap.add_argument("--audit-input", help="existing audit report to resume from")
    ap.add_argument("--design-input", help="design document to resume from")
    ap.add_argument("--proposal-input", help="proposal document to build from")
    ap.add_argument("--proposal-accepted", action="store_true", help="confirm that the supplied proposal was accepted")
    ap.add_argument("--stages", help="comma-separated ordered subset of: audit,design,diagram,propose,build")
    ap.add_argument("--intent", choices=("remediation", "migration"), default="remediation")
    ap.add_argument("--target", help="target engine; defaults to PostgreSQL 18 except build, which reads the accepted proposal/design")
    ap.add_argument("--good-enough", type=float, default=9.0)
    ap.add_argument("--max-flag-ratio", type=float, default=0.10)
    ap.add_argument("--skills", default=str(HERE.parent / "skills"))
    ap.add_argument("--model")
    ap.add_argument("--delegate-model")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--budget-usd", type=float)
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args(argv)
    target = a.target or ("the engine specified in the accepted proposal and design"
                          if a.stages and a.stages.strip() == "build" else "PostgreSQL 18")

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
            raise Usage("a new-database workflow has no audit stage")
        if "build" in stages and "propose" in stages:
            raise Usage("DDL generation must be a separate run after proposal review and acceptance")
        if "build" in stages and stages != ["build"]:
            raise Usage("build is a standalone final stage; run design/diagram/propose first, then accept and build separately")
        if "build" in stages and stages != ["build"]:
            raise Usage("build is a standalone final stage; run design/diagram/propose first, then accept and build separately")
        if "build" in stages and (not a.proposal_input or not a.proposal_accepted):
            raise Usage("build requires --proposal-input and explicit --proposal-accepted")
        if "build" in stages and not a.design_input:
            raise Usage("build requires --design-input for the design referenced by the accepted proposal")
        if "audit" in stages and a.mode == "existing" and not (a.ddl or a.dsn_env):
            raise Usage("existing-database audit requires --ddl or --dsn-env")
        if a.mode == "new" and "design" in stages and not a.requirements:
            raise Usage("new-database design requires --requirements")

        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = out / "runs" / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        ctx = loop.Ctx(repo=out, skills=skills, test_cmd="", base="HEAD", cap=1,
                       model=a.model, delegate_model=a.delegate_model, concurrency=a.concurrency,
                       budget=a.budget_usd, timeout=a.timeout, dry=False, run_dir=run_dir,
                       claude_bin=os.environ.get("HARNESS_CLAUDE", "claude"))

        audit_path = pathlib.Path(a.audit_input).resolve() if a.audit_input else out / "audit"
        design_path = pathlib.Path(a.design_input).resolve() if a.design_input else out / "design"
        if "audit" in stages:
            cmd = [sys.executable, str(HERE / "dbreview.py"), "--out", str(out / "audit-run"),
                   "--intent", a.intent, "--target", target, "--good-enough", str(a.good_enough),
                   "--max-flag-ratio", str(a.max_flag_ratio), "--skills", str(skills), "--audit-only"]
            for spec in a.ddl or []:
                cmd += ["--ddl", spec]
            for var in a.dsn_env or []:
                cmd += ["--dsn-env", var]
            if a.model:
                cmd += ["--model", a.model]
            if a.delegate_model:
                cmd += ["--delegate-model", a.delegate_model]
            if a.budget_usd is not None:
                cmd += ["--budget-usd", str(a.budget_usd)]
            cmd += ["--concurrency", str(a.concurrency), "--timeout", str(a.timeout)]
            proc = subprocess.run(cmd, check=False)
            if proc.returncode:
                raise loop.HarnessError(f"audit harness exited with status {proc.returncode}")
            audit_path = out / "audit-run" / "audit"
            (out / "audit").mkdir(exist_ok=True)
            # Keep the canonical workflow path clear while retaining dbreview's standalone output.
            for child in audit_path.iterdir():
                dest = out / "audit" / child.name
                if child.is_file():
                    dest.write_bytes(child.read_bytes())
                elif child.is_dir():
                    import shutil
                    shutil.copytree(child, dest, dirs_exist_ok=True)
            gate_text = read_text(out / "audit-run" / "gate.md", "audit gate")
            (out / "gate.md").write_text(gate_text)
            scores = json.loads(read_text(out / "audit" / "scores.json", "audit scores"))
            failed_gate = []
            for name, score in scores.get("databases", {}).items():
                if score["score"] < a.good_enough or score["critical"] or score["high"] or score["usage"] in ("unused", "copy") or score["flags"] > a.max_flag_ratio * max(1, score["objects"]):
                    failed_gate.append(name)
            (out / "gate-status.json").write_text(json.dumps({"requires_proposal": failed_gate,
                                                               "passed": sorted(set(scores.get("databases", {})) - set(failed_gate)),
                                                               "good_enough": a.good_enough,
                                                               "max_flag_ratio": a.max_flag_ratio}, indent=2) + "\n")
            if a.mode == "existing" and not a.stages and not failed_gate and a.intent != "migration":
                (out / "workflow.json").write_text(json.dumps({"mode": a.mode, "stages_requested": stages,
                                                                "stages_completed": ["audit"], "status": "gate-passed",
                                                                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat()}, indent=2) + "\n")
                loop.log("all databases passed the score and risk gates; no redesign, diagrams, or proposal required")
                return EXIT_OK

        audit_text = ""
        if a.mode == "existing":
            if audit_path.is_dir():
                audit_text = "\n\n".join(p.read_text(errors="replace") for p in sorted(audit_path.glob("*/summary.md")))
            elif a.audit_input:
                audit_text = read_text(audit_path, "audit")
            elif any(s in stages for s in ("design", "propose")):
                raise Usage("design/propose without the audit stage requires --audit-input")

        design_files = sorted(design_path.glob("*.md")) if design_path.is_dir() else []
        design_text = "\n\n".join(p.read_text(errors="replace") for p in design_files)
        if a.design_input:
            external_design = pathlib.Path(a.design_input).resolve()
            design_files = [external_design]
            design_text = read_text(external_design, "design")
        requirements = read_text(pathlib.Path(a.requirements).resolve(), "requirements") if a.requirements else ""
        if "design" in stages:
            source_inputs = "\n".join(f"- {pathlib.Path(spec.split('=', 1)[-1]).resolve()}" for spec in (a.ddl or []))
            prompt = (f"Run dbdesign (`{loop.skill_path(ctx, 'dbdesign')}`). Mode: {'new database' if a.mode == 'new' else 'audited redesign'}. Target engine: {target}.\n"
                      f"Requirements/context:\n{requirements or '(see source files in the working directory)'}\n\nAudit evidence:\n{audit_text or '(none; new database)'}\n\n"
                      f"Existing source DDL paths (read as needed):\n{source_inputs or '(none)'}\n\n"
                      "Return a complete reviewable design as one Markdown file named design.md. Keep assumptions and unresolved questions explicit.")
            cwd = pathlib.Path(a.requirements).resolve().parent if a.requirements else (pathlib.Path(a.ddl[0].split("=", 1)[-1]).resolve().parent if a.ddl else out)
            files = skill_call(ctx, "design", "dbdesign", prompt, out / "design", cwd)
            design_files = files
            design_text = "\n\n".join(p.read_text() for p in files)
        elif not design_text and any(s in stages for s in ("diagram", "propose", "build")):
            raise Usage("diagram/propose/build requires a prior design artifact, --design-input, or the design stage")

        diagram_paths = sorted((out / "diagrams").glob("*.drawio"))
        if "diagram" in stages:
            prompt = (f"Run dbdiagram (`{loop.skill_path(ctx, 'dbdiagram')}`). Create both the modelo entidad relación and modelo relacional as native editable draw.io XML.\n"
                      f"Design:\n{design_text}\n\nAudit/source context:\n{audit_text or '(new database)'}\n\n"
                      "Return exactly two files, er-model.drawio and relational-model.drawio, each containing a complete mxfile XML document.")
            cwd = pathlib.Path(a.design_input).resolve().parent if a.design_input else out
            diagram_paths = skill_call(ctx, "diagram", "dbdiagram", prompt, out / "diagrams", cwd)
        elif "propose" in stages and not diagram_paths:
            raise Usage("proposal requires diagram artifacts; include the diagram stage or provide .drawio files in --out/diagrams")

        if "propose" in stages:
            diagrams = "\n".join(f"- {p.name}: {p}" for p in diagram_paths)
            design_sources = "\n".join(f"- {p}" for p in design_files)
            prompt = (f"Run dbpropose (`{loop.skill_path(ctx, 'dbpropose')}`) to prepare the final reviewable recommendation. Intent: {a.intent}. Target: {target}.\n"
                      f"Audit evidence folder: {audit_path if audit_text else '(new database; no audit)'}\n"
                      f"Audit summary:\n{audit_text or '(new database; no audit)'}\n\nDesign:\n{design_text}\n\n"
                      f"Design artifact paths (include these in the proposal):\n{design_sources}\n\n"
                      f"Diagrams (include paths and explain views):\n{diagrams}\n\n"
                      "Read the relevant per-file audit evaluations as needed and cite their finding IDs and file:line evidence. Check that design and diagrams agree.\n"
                      "Return a proposal.md with priorities, rationale, risks, sequencing, validation, and unresolved questions. Do not apply changes.")
            skill_call(ctx, "propose", "dbpropose", prompt, out / "proposal", out)
        if "build" in stages:
            proposal_path = pathlib.Path(a.proposal_input).resolve()
            proposal_text = read_text(proposal_path, "accepted proposal")
            prompt = (f"Run dbbuild (`{loop.skill_path(ctx, 'dbbuild')}`). The user explicitly confirms acceptance of proposal `{proposal_path}`. "
                      f"Generate reviewable DDL for {target}. The accepted proposal and design are authoritative; if their engine or structure conflicts, stop and report it.\n\nAccepted proposal:\n{proposal_text}\n\n"
                      f"Approved design source: {design_files[0] if design_files else a.design_input}\n\nDesign:\n{design_text}\n\n"
                      f"Related diagram artifacts:\n{chr(10).join(str(p) for p in diagram_paths) or '(not supplied in this run)'}\n\n"
                      "Generate ordered .sql files only. Validate syntax and consistency against the design. Do not connect to or modify a database.")
            skill_call(ctx, "build", "dbbuild", prompt, out / "ddl", out)
        (out / "workflow.json").write_text(json.dumps({"mode": a.mode, "stages_requested": stages,
                                                        "stages_completed": stages, "finished_at": dt.datetime.now(dt.timezone.utc).isoformat()}, indent=2) + "\n")
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
