# Proposal — From Review and Controls to a Remediation Plan

This reference governs **Propose** mode. It consumes a review (Review mode's findings, scores, gate
and endpoint inventory) and a controls design (Design mode's `controls.md`) when those exist. **Do not
re-run the review or re-design the controls here.** If an input is missing, say so and scope the
proposal to what exists — never imply a missing review or design was done.

Treat review scores as evidence, not a substitute for judgement. Read the caps and the gate: an open
Critical caps a domain at 2.0, an open High at 6.0; 9.0 is the score threshold, and the gate also
needs authorisation and CSRF defence on every state-changing endpoint, no secret in VCS or artefacts,
a slow salted KDF for passwords and no known-exploited reachable dependency.

## Decisions per domain

Use each domain's band as the starting posture, then explain any evidence-based override:

| Score band | Starting posture |
|---|---|
| 9.0–10 | **Keep** — and add the guardrail that keeps it there |
| 7.0–8.9 | **Fix** — targeted corrections inside the existing controls (one missing check, one raw output, one dependency bump) |
| 5.0–6.9 | **Rework** — replace the pattern in this domain (introduce a central authorisation layer, move to an autoescaping template engine, adopt the framework's identity component, introduce a secrets store) |
| 0–4.9 | **Rebuild** — the domain's controls are redesigned from `controls.md` and migrated behind a feature flag or route by route |
| Dead endpoint or unused dependency | **Remove** — state the evidence (no route reference, no traffic, no import) and the confirmation needed |

Any open Critical gets a corrective decision **in the first change window**, even when the overall
score is high.

## The rule that dominates: fix the class, not the instance

A review finds instances; attackers find the one the review missed. For every finding, ask **what
shared cause let it happen** and fix there (SE §27.5.4, p.1019 — fix the whole class of bug and update
the toolchain so similar bugs are found):

| Instances | Shared cause | Class fix | Class guard |
|---|---|---|---|
| Several concatenated queries | No query layer, or a raw escape hatch | One query builder/ORM path; remove the raw helper | Semgrep/CodeQL rule banning raw SQL with interpolation in CI |
| Several XSS sinks | Raw-output helpers, a non-escaping engine | Autoescaping by default; one sanitiser for rich text | Lint rule on raw-output helpers; CSP to contain what's left |
| Several IDORs | Handlers fetch by ID directly | Ownership/tenant predicate in the repository layer | A test that walks every object endpoint with a second user's session |
| Missing authz on new routes | Per-handler checks | Central policy layer, deny by default | A test that enumerates the router and fails on any route without a declared permission |
| CSRF gaps | Anti-forgery opt-in per form | Global anti-forgery + `SameSite` | Test that state-changing routes reject requests without a token |
| Secrets in code | No secrets store | Store + workload identity | Secret scanning as a blocking pre-commit and CI step |
| Vulnerable dependencies | No update cadence | Automated update PRs + SCA gate | CI blocks on known-exploited/critical-reachable |
| Missing or inconsistent security headers | Headers set per handler | One middleware applying the header contract per route class | Table-driven header test over one route of each class |
| Several ad-hoc URL checks | No shared URL helper | One parse-and-allow-list function for redirects and fetches | Lint rule banning string checks on URLs; a test table of hostile URLs |
| Excessive data exposure on several endpoints | Entities serialised directly | Response DTOs per role | Test diffing response keys against the spec per role |
| Shadow or zombie API versions | No inventory, no sunset | Reconciled inventory, `410` for retired versions | CI spec-vs-route diff; a request per retired version expecting `410` |
| Unlimited credential and OTP endpoints | No shared limiter | One limiter keyed on principal and account, on route templates | Test that a burst over the limit gets `429` on every version |

Per-instance patches are acceptable only for **containment** while the class fix lands, and are
listed as such.

## Every fix starts red

Each remediation step names the **failing test that demonstrates the defect** before the fix — an
injection payload that reaches the sink, a second user's ID that returns data, a request without a
token that succeeds — run locally or against an environment the user owns and named. The fix is done
when that test passes and the class guard is in place. Build it through
[tdd](../../development/tdd/SKILL.md); urgent containment through
[hotfix](../../operations/hotfix/SKILL.md).

## Sequencing

Order the work:

1. **Containment.** Rotate then remove leaked secrets — deleting a secret from HEAD doesn't remove it
   from history, forks, caches or the attacker's copy; purge history only after rotation. Close
   exploitable injection and authorisation holes on anonymous and public endpoints (a narrow patch or
   a disabled feature is fine here). Upgrade known-exploited reachable dependencies. Invalidate
   sessions or tokens if a signing secret leaked.
2. **Systemic fixes at the shared cause**, in dependency order: the authentication component and
   session handling first (everything else trusts them), then the central authorisation layer, then
   the query layer and output encoding, then crypto and secrets.
3. **Guardrails.** Lint and SAST rules for each fixed class, secret scanning, SCA gate, the
   route-enumeration authorisation test — so the class can't come back. Coordinate CI changes with
   [pipelines](../../infrastructure/pipelines/SKILL.md).
4. **Configuration.** Production config review, error handling, security headers (CSP report-only
   first, then enforce), management endpoints off.
5. **Dependencies and licences.** Lockfiles and pins, EOL upgrades (one major at a time, tests green),
   SBOM per release, licence decisions recorded.
6. **Logging and cleanup.** Security event catalogue implemented and shipped off-host; secrets
   scrubbed from logs; dead endpoints and unused dependencies removed after confirmation.

Respect the **service trust graph** from R5: fix the issuer before the consumers (a token-signing
service before the services that accept its tokens), and never revoke a credential before its
replacement is deployed everywhere that uses it.

## Proposal skeleton — `analysis/appsec/proposal.md`

```markdown
# <Service> — Application security remediation proposal
> Inputs: review <path, commit, rubric v1.0> · controls <path or "none">.

## Summary
Score <x> (<band>), gate <pass/fail — failing conditions>. <n> Critical, <n> High (<OWASP categories>).
Recommendation in one paragraph.

## Decisions per domain
| Domain | Score | Decision | Reason (finding IDs) |
|---|---:|---|---|

## Containment (first change window)
| # | Finding | Action | Red test | Rollback | Owner |
|---|---|---|---|---|---|

## Class fixes
| # | Findings | Shared cause | Class fix | Red test | Class guard | Depends on |
|---|---|---|---|---|---|---|

## Guardrails added to CI

## Configuration, dependency and licence changes

## Risks of the remediation itself, and what we accept

## Open questions
```

Every step names its finding IDs, its red test and — for a class fix — its guard. A step missing any
of them is not ready to schedule.
