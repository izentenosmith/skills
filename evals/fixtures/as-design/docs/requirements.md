# ledgerly — requirements (kickoff notes)

## What we're building

A multi-tenant invoicing SaaS for agencies and freelancers. Each customer organisation is a
**tenant**. Users belong to exactly one tenant and have one of three roles: `owner`, `accountant`,
`viewer`. A small internal support team must be able to look at a tenant's account when a customer
asks for help.

- **Web app**: a single-page app served from `app.ledgerly.example`, talking to a REST API on
  `api.ledgerly.example`.
- **Invoices**: create, edit while draft, send, mark paid, void. Owners and accountants can create and
  send; viewers read only. Voiding a sent invoice is owner-only.
- **Receipts**: users upload receipts (PDF, PNG, JPEG, and some customers send HEIC and SVG) and
  attach them to expenses. Receipts are shown inline in the app.
- **Partner API**: accounting partners (bookkeeping tools) pull invoices and push payment status for
  the tenants that connect them. Partners authenticate with an API key we issue per partner per
  tenant.
- **Webhooks**: we notify partners when an invoice is sent or paid.
- **GraphQL**: partners asked for a GraphQL endpoint as well as REST.

Data: customer names, addresses, tax IDs, bank details on invoices, amounts. Some tenants are in the
EU. We expect card payments later through a payment provider (out of scope for v1).

## What the team proposed

These came up in the kickoff. Engineering liked them because they are quick to build:

1. **Auth**: issue a JWT on login, store it in `localStorage`, and make it valid for 30 days so users
   don't have to log in again during a month-end close.
2. **CORS**: set `Access-Control-Allow-Origin: *` on the API so partners can integrate from anywhere.
3. **Receipts**: serve uploaded receipts straight from `app.ledgerly.example/receipts/<file>` "for
   simplicity", with the content type the browser sent at upload.
4. **Partner keys**: partners pass the key as `?api_key=` on each request — easiest for their
   scripts. We'll store keys in the `partners` table so support can read them out if a partner loses
   theirs.
5. **CSRF**: use the double-submit cookie pattern (a `csrf` cookie compared with an `X-CSRF` header).
6. **IDs**: invoices get sequential integer IDs (`/invoices/1042`) because customers like short
   numbers. The SPA only shows a tenant its own invoices, so the API can return an invoice by ID.
7. **GraphQL**: leave introspection and the GraphiQL playground on in production so partners can
   explore the schema.
8. **Support access**: support staff get a "log in as tenant" button.

## Non-functional

- Month-end close is the busiest time: ~40 requests/second per large tenant for a few hours.
- Partners poll every minute; one partner had a bug last year that sent 3,000 requests/second.
- We'll deploy v1 in Q3 and expect a v2 of the partner API within a year.
