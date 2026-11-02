# Proposal — From Review and Model to a Risk-Treatment Plan

This reference governs **Propose** mode. It consumes a review (findings, scores, gate) and a threat
model (`threat-model.md` — risk register, hazard × mechanism matrix, requirements) when those exist.
**Do not re-run the review or re-model here.** If an input is missing, say so and scope the plan to
what exists — never imply a missing review or model was done.

Treat scores as evidence, not a substitute for judgement. Read the caps and the gate: an open
Critical caps a domain at 2.0, an open High at 6.0; 9.0 is the threshold, and the gate also needs
two independent mechanisms per serious hazard, an authentication and authorisation decision on every
boundary crossing, and an owner and treatment for every risk.

## Decisions per risk

Every risk in the register, and every Critical/High finding, gets exactly one decision:

| Decision | Means | When | Required fields |
|---|---|---|---|
| **Eliminate by design** | Remove the hazard: don't hold the data, split the component, drop the feature, remove the central key store (S3) | Always considered first; preferred whenever the function survives without the hazard | What is removed, what replaces the function, what it costs |
| **Mitigate** | Add or strengthen mechanisms until the hazard has two independent ones and residual risk is within appetite (S22) | The hazard can't be removed | Mechanisms (IDs), the requirement each satisfies, the test that proves it, the skill that builds it |
| **Transfer** | Move the loss to a party better placed to bear or control it — insurer, provider, contract | The loss is financial and someone else controls the cause | Who now bears it, the contract or policy, what *isn't* transferred (reputation, regulatory duty, the customer's harm) |
| **Accept** | Live with it, knowingly | Residual risk is within appetite and treatment costs more than the loss | **Owner** (who bears the loss — S1), **expiry** (≤ 12 months; re-decide then), the reason, the trigger that reopens it |

Use the domain's score band as the starting posture:

| Score band | Starting posture |
|---|---|
| 9.0–10 | **Keep** — targeted mitigations only |
| 7.0–8.9 | **Strengthen** — add the missing mechanism, binding or trace inside the current design |
| 5.0–6.9 | **Rework** — change the pattern in this domain (introduce a stated access-control model, move authorisation to the data layer, replace static authenticators) |
| 0–4.9 | **Redesign** — re-model the domain from scope down before building more on it |

Two rules:

- **Any open Critical gets a decision in the first change window**, even when the overall score is
  high. If it's live and exploitable, containment comes before any design work.
- **"Accept" is never a default.** An acceptance without an owner who bears the loss, or without an
  expiry, is an open finding (S1, S24).

## Sequencing

Order the plan so each step makes the next one safer:

1. **Containment.** Anything live and exploitable now — an unauthenticated crossing to a high-value
   asset, a leaked or fleet-wide key, a single-credential path to an irreversible action, **weak
   authentication on a privileged path** (SMS or other phishable or SIM-swappable MFA on admin or
   approver roles, password-only or shared admin access, a recovery flow that bypasses the second
   factor), and a **fail-open fallback** on a control that guards money, identity or data. Rotate
   leaked keys before removing them; disable the path before redesigning it. Each containment step
   names its rollback.

   **Exploitability decides the step; the domain decides only where the full fix lives.** A
   protocol or policy finding that is live and exploitable gets an **interim containment** here —
   enrol privileged roles on an authenticator app or hardware key and turn the SMS factor off for
   them, hold high-risk actions while a control is down, disable a self-service feature — and its
   complete treatment stays in its own phase below. Filing a live privileged-access weakness under
   "policy and protocols" because that is its domain leaves it open for the whole redesign.
2. **Eliminate hazards by design.** Remove data, keys, privileges and central stores that needn't
   exist — before adding controls around them. Removing a hazard can delete whole rows of later work.
3. **Boundary controls.** Authentication and authorisation on every crossing, in boundary order from
   the least-trusted zone inward; least privilege for components; no confused deputies.
4. **Policy and protocols.** The stated access-control model, separation of duty and dual control,
   transaction binding, key lifecycle, revocation.
5. **Detection and response.** Signals, owners, response times, seeded tests; evidence outside the
   admins' reach; the incident plan.
6. **Assurance.** Requirements traced to tests; hostile review; disclosure route; re-run triggers
   written into the model.

Within a step, order by risk score; where two items share a mechanism, do the shared one first.
Respect dependencies the model shows: transaction binding needs the key lifecycle; data-layer
authorisation needs the access-control model.

## Who carries each item

The plan routes work; it doesn't do it. Every item names the skill and owner that carries it:

| Item is about | Goes to |
|---|---|
| Code — authn/authz checks, input handling, session and token handling, crypto use, dependencies | [appsec](../appsec/SKILL.md) |
| Platform — hosts, accounts, network exposure, storage, backups, logging, deletion locks | [hardening](../hardening/SKILL.md) |
| CI/CD — build and deploy trust, signing, secrets in pipelines, who can deploy | [pipelines](../../infrastructure/pipelines/SKILL.md) |
| Network — zones, flows, segmentation, addressing | [netdesign](../../networking/netdesign/SKILL.md) |
| Infrastructure code that implements any of the above | [terraform](../../infrastructure/terraform/SKILL.md) |
| A design question the threat model surfaced but can't settle | [architect-deep-dive](../../development/architect-deep-dive/SKILL.md) |
| A new capability to build test-first against the security requirements | [agent-brief](../../development/agent-brief/SKILL.md) → [acceptance-tests](../../development/acceptance-tests/SKILL.md) |

## `proposal.md` template

```markdown
# <System> — Risk-treatment plan
> Inputs: review <path, version, score, gate> · threat model <path, version> (or "not available — scoped to …").
> Tier: <…>. Rubric v1.0.

## Summary
Score <x> (<band>), gate <pass/fail — conditions>. <n> Critical, <n> High. Decisions: <n> eliminate · <n> mitigate · <n> transfer · <n> accept.

## Decision register
| Risk / finding | Score | Decision | Mechanisms / change | Requirement | Verified by | Skill | Owner | Due / expiry |
|---|---:|---|---|---|---|---|---|---|

## Sequence
| Step | Phase | Items | Depends on | Rollback | Done when |
|---|---|---|---|---|---|
| 1 | Containment | TM-BND-01 | — | re-enable route F7 behind flag | F7 requires mTLS + tenant check in prod |

## Accepted risks
| Risk | Owner (bears the loss) | Reason | Expiry | Reopen trigger |

## Gate after the plan
Each gate condition, and which step makes it pass.

## Open questions
Each with the decision it blocks.
```

Then stop. The plan is done when every risk has a decision, every Critical/High has a step, and every
step names its skill, owner, rollback and "done when".
