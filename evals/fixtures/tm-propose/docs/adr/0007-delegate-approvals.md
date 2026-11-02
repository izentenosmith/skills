# ADR-0007: Delegating approvals during absence

Status: accepted · 2026-06-02

## Context
Approvers go on leave and large payouts queue up.

## Decision
- Any user with `payout_approver` can delegate their approval rights to **any other user** in
  `admin-console` → Settings → Delegation, for up to 30 days.
- The delegate receives `payout_approver` for the period. Delegations are recorded in the
  `delegations` table.
- No approval from security or HR is needed; it is self-service to keep it quick.

## Consequences
No queue during holidays.
