# brightcart — schema audit summary (excerpt), rubric v1.2, schema of 2026-09-30

## Needs-data flags (not scored)
- **AUD-07** 🔬 `ix_order_status` indexes a low-cardinality `status` column — is it used at all?
- **AUD-09** 🔬 Support reports slow customer lookups; `ix_customer_email` exists — what does the plan do?
- **AUD-11** 🔬 `order_line` carries an index per FK; its write volume is not in the DDL.
