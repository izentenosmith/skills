# Ops Console

Owner: Courier Operations. Internal web app for courier support.

- **Who uses it:** our Tier-2 support team and Tier-1 agents from our outsourced support partner
  (three sites, about 140 agents). Everyone signs in with corporate SSO; partner agents have
  contractor accounts in our identity provider.
- **Roles:** `tier1`: view a courier, edit profile. `tier2`: everything in tier1, plus refunds,
  deactivation and manual balance adjustments.
- **How it reaches accounts-svc:** the console's backend calls the accounts-svc internal API with one
  service token (header `X-Ops-Token`) from its config. The role check happens in the console.
  accounts-svc records the caller of every internal call as `ops-console`.
- **Audit:** the console keeps its own action log (agent, courier, which fields changed) for 30 days.
