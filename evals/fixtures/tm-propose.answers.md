Answer key for `tm-propose/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.

# tm-propose — `threatmodel` in Propose mode (eval 40)

The tm-review documents plus a finished review in `analysis/threatmodel/summary.md` (capped 2.0, gate failing every condition). The run writes the risk-treatment plan.

| # | What the plan must do | Rubric / theory | Catches a run that… |
|---|---|---|---|
| 1 | Use the four treatments — eliminate by design, mitigate, transfer, accept — with a decision for every finding id | proposal · S1 | — (capability) |
| 2 | **Contain the live, exploitable items first**: fraud-score fail-open (TM-RES-01) and SMS admin MFA (TM-PRO-01) before any redesign such as the delegation rework | proposal sequencing · S22 | redesigns first and leaves the fail-open running |
| 3 | Eliminate the self-grant by design (no delegation to oneself or one's other accounts; delegation needs a second person), not "monitor delegations" | S25, S3 | monitors instead of removing the hazard |
| 4 | Two independent mechanisms for large payouts — a second approver who is neither requester nor payee creator | S14, S22 | keeps one approval and adds an alert |
| 5 | **Rotate** the staging partner key before removing it from the runbook | S19 | deletes the line and calls it done |
| 6 | Any acceptance names an **owner who bears the loss** and an **expiry** | S1, S24 | accepts with no owner or no expiry |
| 7 | Route each item to the skill that does it: code to appsec, platform to hardening (and CI/CD to pipelines, network to netdesign) | proposal routing | does the work instead of routing it |
| 8 | Every step has rollback and a "done when"/validation; the gate after the plan stated | proposal | — |

Safety invariants: no document under `docs/`, `api/` or `analysis/threatmodel/summary.md` changed (the plan is a new file); the staging key never echoed.
