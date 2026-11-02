# payouts — Threat-model review summary
> Components: 8 · trust boundaries: 4 · crossings: 11 · assets: 6 · serious hazards: 5. Evidence as of
> architecture rev 14 (2026-09-30), ADR-0003/0005/0007, openapi 2.3.0; rubric v1.0. Tier: high-assurance (moves money).

## Scores
| scope | adversaries | boundaries | policy | protocols | resilience | **System** |
|---:|---:|---:|---:|---:|---:|---:|
| 5.0 | 6.0 | 5.0 | 2.0 | 5.0 | 4.0 | **2.0** (uncapped 4.6) |

Arithmetic per domain: base = Σ points / (2 × criteria) × 10, then caps (Critical → 2.0, High → 6.0).
- scope: 5 of 8 criteria 🟡/🟢 → base 5.0; High open (TM-SCO-02) caps at 6.0 → **5.0**
- adversaries: base 6.3; High open (TM-ADV-01) → **6.0**
- boundaries: base 5.0 → **5.0**
- policy: base 4.4; Critical open (TM-POL-01) → **2.0**
- protocols: base 5.0 → **5.0**
- resilience: base 4.0 → **4.0**

## Severity tally · Needs-data flags
Critical 1 · High 8 · Medium 1 · Low 0.
🔬 not scored: whether delegations are ever reviewed; whether the bank can add a timestamp to the
webhook; the scopes a partner key actually carries; whether merchants are told when support resets MFA
beyond the e-mail.

## Asset register
| Asset | Class | Owner | Why an adversary wants it |
|---|---|---|---|
| Merchant balances | confidential (money) | payments-platform | cash out |
| Payees (bank accounts) | confidential | payments-platform | redirect payouts |
| Approval rights | integrity-critical | ops | approve your own fraud |
| Admin sessions | integrity-critical | ops | everything above |
| Bank signing key (KMS) | restricted | payments-platform | forge payment files |
| Webhook secret | restricted | payments-platform | forge settlements |

## Findings
| ID | Object | Anti-pattern | Conf. | Theory | Severity | Evidence |
|---|---|---|---|---|---|---|
| TM-POL-01 | Large-payout approval | One approver for an irreversible action; the approver can also create the payee and be the requester's manager | ✅ | Separation of duty and dual control (S14) | Critical | ADR-0003 |
| TM-POL-02 | Delegate approvals | Self-grantable role: an approver can delegate to any user, including a second account of their own | ✅ | Every role asks who can grant it (S25) | High | ADR-0007 |
| TM-PRO-01 | Admin sign-in | Admin MFA by SMS one-time code | ✅ | Freshness / no SMS for high-value (S17, S5) | High | admin-console.md §Sign-in |
| TM-PRO-02 | Settlement webhook | Static HMAC, no timestamp or nonce: replayable; "latest status wins" | ✅ | Freshness; revocation and time (S17, S20) | High | ADR-0005; runbook |
| TM-BND-01 | Service-to-service calls | Internal network trusted; no authentication between services | ✅ | Compartmentalise (S9); enforce at the right layer (S11) | High | architecture.md §Trust |
| TM-BND-02 | `PUT /partner/v1/merchants/{id}/payees` | Partner can replace any merchant's payee; no merchant–partner binding stated | ⚠️ | Enforce at the right layer (S11) | High | openapi.yaml |
| TM-ADV-01 | Support MFA reset | Recovery by knowledge questions over the phone; insider/pretexting path | ✅ | Insiders and the people you trust (S7); people err predictably (S8) | High | admin-console.md §Support |
| TM-RES-01 | fraud-score outage | Fail-open: payouts proceed without a score | ✅ | Two mechanisms; fail to a safe state (S22) | High | architecture.md step 2; runbook |
| TM-SCO-01 | docs/threat-model.md | Model from 2025-05 covers merchant-web only; predates partner-api; internal services out of scope | ✅ | Assurance is continuous (S24); model verified against the system (S27) | Medium | threat-model.md |
| TM-SCO-02 | Runbook | A staging partner API key pasted in the runbook (value not reproduced here) | ✅ | Key management (S19) | High | runbook.md §Testing |

## Hazard × mechanism matrix (serious hazards)
| Hazard | Mechanisms today | Count |
|---|---|---:|
| Fraudulent large payout | one approval | 1 |
| Payout to an attacker's bank account | e-mail confirmation (merchant path only) | 1 |
| Admin account takeover | password + SMS | 1 |
| Forged or replayed settlement | static HMAC | 1 |
| Lateral movement from one service | none | 0 |

## What is working well
TLS on every hop; the bank signing key held in KMS and non-exportable; the audit log shipped to a
separate security account. Keep all three.

## Gate
- Score ≥ 9.0: **fail** (2.0).
- No open Critical/High: **fail** (1 Critical, 8 High).
- Two independent mechanisms per serious hazard: **fail** (every hazard has 0–1).
- Every trust-boundary crossing names its authentication and authorisation decision: **fail**
  (service-to-service crossings have none; the partner payee crossing has no authorisation decision).
- Every risk has an owner and a treatment: **fail** (no risk register).
- 🔬 ≤ 10%: pass (4 of 46 objects).
