# Incident log: renewal emails bounce for Gmail subscribers (2026-11-09, open)

- 06:40 UTC first bounce: `550 5.7.26 This mail is unauthenticated` from gmail-smtp-in.l.google.com
- 07:55 UTC dara notices the bounce rate on the mail dashboard: 100% for @gmail.com, 0% elsewhere
- 08:05 UTC L-41 opened

Status at 09:30 UTC: still bouncing. 1,180 renewal receipts not delivered so far. Suspect the DKIM key rotation on Saturday. Nobody is on it yet.
