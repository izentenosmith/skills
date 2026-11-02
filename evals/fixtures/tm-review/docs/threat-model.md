# Payouts — threat model

Version 1.0 · 2025-05-14 · scope: `merchant-web` and `payouts-svc`

## Assets
- Merchant balances
- Merchant bank details

## Threats (STRIDE)
| # | Threat | Mitigation |
|---|---|---|
| 1 | Spoofing a merchant session | Session cookies, HttpOnly, Secure |
| 2 | Tampering with payout amount in the browser | Amount recomputed server-side |
| 3 | Information disclosure of bank details | TLS; masked in the UI |
| 4 | Denial of service on merchant-web | Load balancer rate limit |

## Out of scope
Internal services (trusted network).
