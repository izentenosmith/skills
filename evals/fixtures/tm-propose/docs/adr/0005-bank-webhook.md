# ADR-0005: Settlement webhook from the bank

Status: accepted · 2025-04-20

## Decision
- The bank posts `POST /webhooks/settlement` with the payout id and status.
- The request carries `X-Signature: hex(HMAC-SHA256(shared_secret, body))`. The shared secret was
  agreed with the bank at onboarding and is stored in KMS-backed secrets.
- `bank-gateway` verifies the signature and forwards the status to `payouts-svc`.
- The body has no timestamp or nonce; the bank's format does not include one and we don't add one.

## Consequences
Simple to implement; matches the bank's sample code.
