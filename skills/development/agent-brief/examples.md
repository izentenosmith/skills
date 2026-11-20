# Examples — a good brief, a bad one, and what separates them

> Read this when you are unsure what a good criterion or a good brief looks like.
> The domain here (exporting invoices) is only an illustration: take the shape, not the content.

## Good and bad sentences

- **Good (behavior):** "When an export is requested for a range longer than the limit, it is rejected with error code `RANGE_TOO_LARGE`."
- **Bad (procedure):** "Open the export handler and add an `if` that compares the two dates."
- **Good (contract):** "The `ExportRequest` type should expose a `Validate(config)` method returning the list of constraint violations."
- **Bad (location):** "Add a switch statement in the export-service source around line 80."
- **Good (criterion):** "The export endpoint returns a rejection with error code `RANGE_TOO_LARGE` when the requested range is longer than the limit."
- **Bad (criterion):** "Range limits should work correctly."

## Good build plan (enhancement)

```markdown
# Build Plan: Export an account's invoices as CSV

**Status:** draft — awaiting approval
**Design:** `.workflow/designs/20261104-0930-invoice-csv-export.md`
**Category:** enhancement
**Summary:** Let an account's billing members download its invoices for a date range as a CSV file.

**Current behavior:**
Invoices can be listed one page at a time through the invoice-list
endpoint. There is no way to take them out in bulk; finance teams copy
them by hand at month end, which is why this is being built now.

**Desired behavior:**
A billing member requests an export for a date range and receives a CSV
with one row per invoice issued in that range, oldest first. A range
longer than the export limit (a default, configurable per account) is
rejected. A range with no invoices returns the header row alone.
Security trigger: fired — an export names an account, and invoices
belong to accounts; the authorisation rule and the abuse case are
criteria below.

**Key interfaces (test seams):**
- The invoice-export handler — the public seam tests drive; on success
  it returns the CSV, on a refused range a rejection carrying error
  code `RANGE_TOO_LARGE`
- `ExportRequest` — should expose validation that returns constraint
  violations rather than raw booleans
- `ExportRange` (domain primitive) — a start and an end date; valid only
  when start ≤ end and the span is within the limit; constructing an
  invalid one fails
- Account config — an `export_max_days` field (with a default) tests can override

**Acceptance criteria** (ordered — first is the tracer-bullet candidate):
- [ ] Tracer bullet: a billing member exporting a range that holds three
      invoices receives a CSV with the header row and three rows, oldest first
- [ ] An invoice issued outside the range does not appear in the export
- [ ] A range longer than `export_max_days` is rejected with error code
      `RANGE_TOO_LARGE`; a range of exactly `export_max_days` is accepted
- [ ] The limit reads from account config, not a hard-coded default
- [ ] Edge case: a range with no invoices returns the header row alone, not an error
- [ ] Edge case: a range whose end is before its start is rejected with
      error code `INVALID_RANGE`
- [ ] Abuse case: a customer name beginning with `=`, `+`, `-` or `@` cannot
      become a spreadsheet formula → the cell is written with a leading `'`
- [ ] Authorisation: export invoices — allowed for a billing member of the
      account; refused, before any invoice is read, for a non-billing member,
      for a member of any other account and for an anonymous caller, on
      every path to it

**Test seams & prior art:**
- Drive tests through the invoice-export handler using the project's
  existing request-driving test harness, mirroring the invoice-list handler tests
- Mirror the table-driven validation tests for the `ExportRange` cases
- For the read path, use the project's integration-test setup

**Parallel tracks:** none — one handler behind one seam; every criterion builds on the tracer bullet

**Deferred by design** (constraints, not work — carried from architect-deep-dive):
- Whether large exports run as background jobs — deferred behind the
  export handler's response contract; forced by the first export that
  outlasts the request timeout

**Decisions on record:**
- `docs/adr/0012-csv-is-the-only-export-format.md` — CSV only, UTF-8 with
  a header row; binding on this build

**Out of scope:**
- Other formats (XLSX, PDF)
- Scheduled or emailed exports
- Changing the default export limit

**Ship checklist** (what no acceptance test can prove):
- [ ] Rollout: behind the `invoice_export` flag, default off; no backfill
- [ ] Rollback: turn the flag off; triggered by exports that time out or return rows from another account
- [ ] Observability: export count, row count and duration on the billing dashboard
- [ ] Docs: the export endpoint and its two error codes added to the API reference

**Base:** — (filled in by tdd before its first slice)

**Acceptance tests** (filled in by stage 3, acceptance-tests — leave empty here):
- **Command:** —

## Revisions
- (empty at creation; TDD's feedback edge appends here)
```

What makes it good: every criterion is one observable behavior through the handler, the list reads top to bottom as a build order, the security block arrived as criteria, the one deferred decision names the boundary that protects it, and what no test can show sits in the Ship checklist.

## Bad build plan

```markdown
# Build Plan: Fix the export bug

**What to do:**
The export thing is broken. Look at the main handler and fix it.
The function around line 80 has the issue.

**Files to change:**
- the export handler source (line 80)
- the invoice domain source (line 42)
```

This is bad because:

- No category, no current-vs-desired behavior
- Vague description ("the export thing is broken")
- References file paths and line numbers that go stale and pre-empt design
- No acceptance criteria — nothing for TDD to slice into red→green cycles
- No prioritization or tracer bullet, so no build order
- No test seams or prior art, forcing TDD to re-design the test plan
- No scope boundaries
