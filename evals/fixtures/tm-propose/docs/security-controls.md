# Security controls

- **TLS everywhere**: TLS 1.2+ at the load balancer and on every service-to-service call; HSTS on
  `merchant-web`.
- **Signing keys in KMS**: payment files to the bank are signed with a key held in KMS; no service can
  export it, and signing calls are logged.
- **Audit log**: every admin-console action and every payout state change is written to an append-only
  audit log shipped to a separate security account that payments-platform engineers cannot modify.
- **Secrets**: service secrets live in the secrets manager, read at start-up.
- **Backups**: payouts-db point-in-time recovery, 35 days.
