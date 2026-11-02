# Admin console

## Sign-in
Ops staff sign in with a username, a password and a **one-time code sent by SMS** to the phone number on
their staff profile. Sessions last 12 hours.

## Roles
| Role | Can |
|---|---|
| `ops_agent` | view merchants, raise payouts on a merchant's behalf, open support cases |
| `payout_approver` | approve payouts ≥ 5,000 USD (ADR-0003) |
| `payee_admin` | create or change a merchant's payee (bank account) |
| `support` | reset a merchant's password or MFA |

## Support tools
When a merchant calls saying they lost access, a `support` agent verifies the caller by asking the
merchant's registered business address, the last payout amount and the date the account was opened, then
resets the merchant's MFA so they can enrol a new device. The merchant gets an e-mail afterwards.
