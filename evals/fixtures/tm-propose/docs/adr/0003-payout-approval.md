# ADR-0003: Approval for large payouts

Status: accepted · 2025-03-11

## Context
Large payouts are where fraud losses concentrate. We want a human to look at them without slowing the
long tail of small payouts.

## Decision
- Payouts of **5,000 USD or more** need **one approval** from a user with the `payout_approver` role.
- `payout_approver` is held by ops managers. The approver can be the manager of the ops agent who raised
  the payout on the merchant's behalf.
- Ops managers also hold `payee_admin`, so they can fix a merchant's bank details during the same call.
- Approval is a single click in `admin-console`; the payout is sent within five minutes.

## Consequences
Fast approvals; one person can handle a merchant's problem end to end.
