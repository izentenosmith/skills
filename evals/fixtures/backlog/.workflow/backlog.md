# Backlog

Wrenfield Roasters: the shop, subscriptions and wholesale. Items in the local format (see `.workflow/tracker.md`). Newest at the bottom.

### L-1 · Subscriptions 2.0
- **Kind:** epic · **State:** doing · **Priority:** — · **Labels:** none
- **Created:** 2026-05-04 · **Updated:** 2026-10-21 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Phase 2 of subscriptions. Everything we didn't get to in phase 1.

**Log**
- 2026-05-04 · created
- 2026-06-01 · doing

### L-2 · Wholesale cafés reorder without calling us
- **Kind:** epic · **State:** doing · **Priority:** — · **Labels:** none
- **Created:** 2026-08-03 · **Updated:** 2026-10-30 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Who: the 40 cafés that buy wholesale. Outcome: cafés place repeat orders themselves; measure: phone and email orders per week drop from ~60 to under 15 by January.

**Log**
- 2026-08-03 · created
- 2026-09-01 · doing

### L-3 · Manually refund double-charged renewals (batch 1)
- **Kind:** task · **State:** done · **Priority:** P1 · **Labels:** toil, unplanned
- **Created:** 2026-09-23 · **Updated:** 2026-09-24 · **Owner:** dara
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Refund the 61 subscribers charged twice on 22 September, by hand in the payment dashboard.

**Log**
- 2026-09-23 · created
- 2026-09-23 · doing
- 2026-09-24 · done · 61 refunds issued

### L-4 · Manually refund double-charged renewals (batch 2)
- **Kind:** task · **State:** done · **Priority:** P1 · **Labels:** toil, unplanned
- **Created:** 2026-10-07 · **Updated:** 2026-10-08 · **Owner:** dara
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Another 23 subscribers charged twice on the 6 October renewal run. Same manual refund.

**Log**
- 2026-10-07 · created
- 2026-10-07 · doing
- 2026-10-08 · done · 23 refunds issued

### L-5 · Manually refund double-charged renewals (batch 3)
- **Kind:** task · **State:** done · **Priority:** P1 · **Labels:** toil, unplanned
- **Created:** 2026-10-28 · **Updated:** 2026-10-29 · **Owner:** dara
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

14 more double charges from the 27 October run. Manual refunds again.

**Log**
- 2026-10-28 · created
- 2026-10-28 · doing
- 2026-10-29 · done · 14 refunds issued

### L-6 · Renewal charged twice for some subscribers
- **Kind:** bug · **State:** done · **Priority:** P1 · **Labels:** prod-incident, unplanned
- **Created:** 2026-09-22 · **Updated:** 2026-09-23 · **Owner:** chen
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

The renewal job retried after a payment-provider timeout and charged 61 subscribers twice. Post-mortem: docs/postmortems/2026-09-22-double-charged-renewals.md.

**Log**
- 2026-09-22 · created · doing
- 2026-09-23 · done · job paused, retry disabled, restarted

### L-7 · Subscribers pause a subscription for up to 8 weeks
- **Kind:** story · **State:** done · **Priority:** P2 · **Labels:** none
- **Created:** 2026-08-25 · **Updated:** 2026-10-14 · **Owner:** ana
- **Parent:** L-1 · **Due:** none · **Continues / duplicates / blocks:** none

Who: subscribers going on holiday. Acceptance criteria: pause 1–8 weeks; no charge while paused; resume email a week before.

**Log**
- 2026-08-25 · created
- 2026-09-29 · doing
- 2026-10-14 · done

### L-8 · Subscribers choose the grind per delivery
- **Kind:** story · **State:** done · **Priority:** P2 · **Labels:** none
- **Created:** 2026-09-01 · **Updated:** 2026-10-21 · **Owner:** bruno
- **Parent:** L-1 · **Due:** none · **Continues / duplicates / blocks:** none

Who: subscribers who brew differently on weekends. Acceptance criteria: grind picker on each upcoming delivery; default from the subscription.

**Log**
- 2026-09-01 · created
- 2026-10-06 · doing
- 2026-10-21 · done

### L-9 · Upgrade Django to 5.2
- **Kind:** task · **State:** done · **Priority:** P3 · **Labels:** none
- **Created:** 2026-09-15 · **Updated:** 2026-10-03 · **Owner:** chen
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

5.0 leaves security support in April.

**Log**
- 2026-09-15 · created
- 2026-09-29 · doing
- 2026-10-03 · done

### L-10 · Gift card balance shown at checkout
- **Kind:** story · **State:** doing · **Priority:** P1 · **Labels:** none
- **Created:** 2026-10-13 · **Updated:** 2026-11-06 · **Owner:** bruno
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Show the remaining balance when a gift card is applied.

**Log**
- 2026-10-13 · created
- 2026-10-27 · doing

### L-11 · Cafés see their own price list when they log in
- **Kind:** story · **State:** doing · **Priority:** P1 · **Labels:** none
- **Created:** 2026-09-08 · **Updated:** 2026-11-05 · **Owner:** bruno
- **Parent:** L-2 · **Due:** none · **Continues / duplicates / blocks:** none

Who: wholesale cafés. Acceptance criteria: a café logged in sees its negotiated prices; anyone else sees retail.

**Log**
- 2026-09-08 · created
- 2026-10-19 · doing

### L-12 · Loyalty points for referrals
- **Kind:** story · **State:** doing · **Priority:** P2 · **Labels:** none
- **Created:** 2026-07-20 · **Updated:** 2026-08-29 · **Owner:** bruno
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Give points when a referred friend subscribes.

**Log**
- 2026-07-20 · created
- 2026-08-18 · doing
- 2026-08-29 · note · waiting to hear from marketing on the points value

### L-13 · Address autocomplete fails for PO boxes
- **Kind:** bug · **State:** doing · **Priority:** P3 · **Labels:** none
- **Created:** 2026-10-29 · **Updated:** 2026-11-04 · **Owner:** bruno
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Typing "PO Box" returns no suggestions and the form won't submit.

**Log**
- 2026-10-29 · created
- 2026-11-02 · doing

### L-14 · Subscription box preview page
- **Kind:** story · **State:** doing · **Priority:** P1 · **Labels:** none
- **Created:** 2026-10-20 · **Updated:** 2026-11-06 · **Owner:** bruno
- **Parent:** L-1 · **Due:** none · **Continues / duplicates / blocks:** none

Show next month's coffees before the box ships.

**Log**
- 2026-10-20 · created
- 2026-11-04 · doing

### L-15 · Gift subscriptions
- **Kind:** story · **State:** todo · **Priority:** P1 · **Labels:** none
- **Created:** 2026-06-02 · **Updated:** 2026-06-02 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Let people buy a subscription for someone else.

**Log**
- 2026-06-02 · created

### L-16 · Roast date printed on the packing slip
- **Kind:** story · **State:** doing · **Priority:** P2 · **Labels:** none
- **Created:** 2026-10-21 · **Updated:** 2026-11-05 · **Owner:** ana
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Who: subscribers. Acceptance criteria: the packing slip shows the roast date of every bag.

**Log**
- 2026-10-21 · created
- 2026-11-03 · doing

### L-17 · Move product images to the new storage bucket
- **Kind:** task · **State:** doing · **Priority:** P3 · **Labels:** none
- **Created:** 2026-10-22 · **Updated:** 2026-11-06 · **Owner:** chen
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

The old bucket's plan ends in December.

**Log**
- 2026-10-22 · created
- 2026-10-30 · doing

### L-18 · Cafés download their invoices as PDF
- **Kind:** story · **State:** todo · **Priority:** P2 · **Labels:** none
- **Created:** 2026-09-08 · **Updated:** 2026-09-08 · **Owner:** unassigned
- **Parent:** L-2 · **Due:** none · **Continues / duplicates / blocks:** none

Who: wholesale cafés' bookkeepers.

**Log**
- 2026-09-08 · created

### L-19 · Shipping confirmation emails sent through the new relay
- **Kind:** story · **State:** doing · **Priority:** P1 · **Labels:** none
- **Created:** 2026-10-06 · **Updated:** 2026-11-05 · **Owner:** ana
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Who: subscribers. Acceptance criteria: the shipping email arrives within 5 minutes of the label being printed.

Blocked: waiting on the platform team's new SMTP relay. They said "end of October".

**Log**
- 2026-10-06 · created
- 2026-10-20 · doing
- 2026-11-05 · note · still blocked

### L-20 · Coupon codes are case-sensitive
- **Kind:** bug · **State:** review · **Priority:** P3 · **Labels:** none
- **Created:** 2026-10-27 · **Updated:** 2026-11-05 · **Owner:** chen
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

"SPRING10" works, "spring10" doesn't. Acceptance criteria: codes match case-insensitively.

**Log**
- 2026-10-27 · created
- 2026-10-31 · doing
- 2026-11-05 · review

### L-21 · Dark mode for the shop
- **Kind:** story · **State:** todo · **Priority:** P1 · **Labels:** none
- **Created:** 2026-10-02 · **Updated:** 2026-10-02 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Customers have asked for it.

**Log**
- 2026-10-02 · created

### L-22 · Bundle builder: mix three coffees in one box
- **Kind:** story · **State:** todo · **Priority:** P1 · **Labels:** none
- **Created:** 2026-10-26 · **Updated:** 2026-11-06 · **Owner:** unassigned
- **Parent:** L-1 · **Due:** none · **Continues / duplicates / blocks:** none

Marta (CEO): THIS IS THE #1 PRIORITY FOR Q4. Drop everything else until it ships.

**Log**
- 2026-10-26 · created
- 2026-11-06 · note · priority raised by Marta

### L-23 · Apple Pay at checkout
- **Kind:** story · **State:** todo · **Priority:** P1 · **Labels:** none
- **Created:** 2026-10-09 · **Updated:** 2026-10-09 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Sales: top priority, both competitors have it.

**Log**
- 2026-10-09 · created

### L-24 · Corporate gifting portal
- **Kind:** story · **State:** todo · **Priority:** P1 · **Labels:** none
- **Created:** 2026-09-30 · **Updated:** 2026-09-30 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Companies buy coffee boxes for their staff at Christmas.

**Log**
- 2026-09-30 · created

### L-25 · Instagram shop sync
- **Kind:** story · **State:** todo · **Priority:** P1 · **Labels:** none
- **Created:** 2026-10-15 · **Updated:** 2026-10-15 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Sync the catalogue to Instagram Shopping.

**Log**
- 2026-10-15 · created

### L-26 · Shipping to Canada
- **Kind:** spike · **State:** todo · **Priority:** P3 · **Labels:** none
- **Created:** 2026-10-12 · **Updated:** 2026-10-12 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Look into Canada.

**Log**
- 2026-10-12 · created

### L-27 · Renew the payment provider's TLS client certificate
- **Kind:** task · **State:** todo · **Priority:** P4 · **Labels:** none
- **Created:** 2026-10-05 · **Updated:** 2026-10-05 · **Owner:** unassigned
- **Parent:** none · **Due:** 2026-11-20 · **Continues / duplicates / blocks:** none

The client certificate checkout uses to talk to the payment provider expires 2026-11-20 00:00 UTC. When it lapses, checkout can't take card payments. The provider needs 3 business days' notice to approve the new certificate; the work itself is about half a day.

**Log**
- 2026-10-05 · created

### L-28 · As a developer I want a cleaner checkout service
- **Kind:** story · **State:** todo · **Priority:** P3 · **Labels:** none
- **Created:** 2026-08-11 · **Updated:** 2026-08-11 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

The checkout code is messy.

**Log**
- 2026-08-11 · created

### L-29 · Gift a subscription to a friend
- **Kind:** story · **State:** todo · **Priority:** P2 · **Labels:** none
- **Created:** 2026-10-30 · **Updated:** 2026-10-30 · **Owner:** unassigned
- **Parent:** L-1 · **Due:** none · **Continues / duplicates / blocks:** none

Buy 3, 6 or 12 months of coffee for someone else, with a gift message.

**Log**
- 2026-10-30 · created

### L-30 · Subscriber referral landing page
- **Kind:** story · **State:** todo · **Priority:** P3 · **Labels:** none
- **Created:** 2025-12-03 · **Updated:** 2026-01-10 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

A landing page for referral links.

**Log**
- 2025-12-03 · created
- 2026-01-10 · note · parked until the loyalty work

### L-31 · Idempotency key on renewal charges
- **Kind:** task · **State:** todo · **Priority:** P2 · **Labels:** follow-up, action:prevent
- **Created:** 2026-09-24 · **Updated:** 2026-09-24 · **Owner:** unassigned
- **Parent:** none · **Due:** 2026-10-15 · **Continues / duplicates / blocks:** none

From the 2026-09-22 double-charge post-mortem (FU-1): every renewal charge carries an idempotency key, so a retried request can't charge twice.

**Log**
- 2026-09-24 · created · from docs/postmortems/2026-09-22-double-charged-renewals.md

### L-32 · Alert when a subscription is charged twice in a day
- **Kind:** task · **State:** done · **Priority:** P2 · **Labels:** follow-up, action:mitigate
- **Created:** 2026-09-24 · **Updated:** 2026-10-20 · **Owner:** chen
- **Parent:** none · **Due:** 2026-10-31 · **Continues / duplicates / blocks:** none

From the 2026-09-22 post-mortem (FU-2).

**Log**
- 2026-09-24 · created
- 2026-10-13 · doing
- 2026-10-20 · done · alert live, tested with a staged double charge

### L-33 · Retry payment-provider timeouts at checkout with backoff
- **Kind:** task · **State:** todo · **Priority:** P3 · **Labels:** none
- **Created:** 2026-10-10 · **Updated:** 2026-10-10 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Checkout fails the order on the first provider timeout. Most of the September and October checkout errors were these.

**Log**
- 2026-10-10 · created

### L-34 · Fail the deploy when checkout returns 5xx after release
- **Kind:** task · **State:** todo · **Priority:** P3 · **Labels:** follow-up, action:prevent
- **Created:** 2026-11-07 · **Updated:** 2026-11-07 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

From the 2026-11-07 checkout 502 incident: a post-deploy health check on /checkout that rolls back automatically.

**Log**
- 2026-11-07 · created · from docs/incidents/2026-11-07-checkout-502.md

### L-35 · Load-test checkout before each release
- **Kind:** task · **State:** todo · **Priority:** P3 · **Labels:** none
- **Created:** 2026-10-16 · **Updated:** 2026-10-16 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

We found the connection-pool limit in production twice.

**Log**
- 2026-10-16 · created

### L-36 · Customers reorder from their order history
- **Kind:** story · **State:** todo · **Priority:** P2 · **Labels:** none
- **Created:** 2026-10-19 · **Updated:** 2026-10-19 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

One click to put a past order back in the cart.

**Log**
- 2026-10-19 · created

### L-37 · Typo on the FAQ page
- **Kind:** bug · **State:** todo · **Priority:** P4 · **Labels:** none
- **Created:** 2026-10-23 · **Updated:** 2026-10-23 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

"recieve" in the shipping answer.

**Log**
- 2026-10-23 · created

### L-38 · Checkout returned 502s after Friday's deploy
- **Kind:** bug · **State:** done · **Priority:** P2 · **Labels:** none
- **Created:** 2026-11-07 · **Updated:** 2026-11-07 · **Owner:** chen
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Checkout returned 502 for about 40 minutes after the 14:05 deploy. Rolled back. Log: docs/incidents/2026-11-07-checkout-502.md.

**Log**
- 2026-11-07 · created · doing
- 2026-11-07 · done · rolled back to 2026.11.06-2

### L-39 · Cafés sign up for a wholesale account themselves
- **Kind:** story · **State:** todo · **Priority:** P2 · **Labels:** none
- **Created:** 2026-09-22 · **Updated:** 2026-09-22 · **Owner:** unassigned
- **Parent:** L-2 · **Due:** none · **Continues / duplicates / blocks:** none

Who: cafés that want to start buying wholesale. Today they email us and we create the account by hand.

**Log**
- 2026-09-22 · created

### L-40 · Customers save more than one delivery address
- **Kind:** story · **State:** todo · **Priority:** P3 · **Labels:** none
- **Created:** 2026-10-28 · **Updated:** 2026-10-28 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Home and office.

**Log**
- 2026-10-28 · created

### L-41 · Renewal emails bounce for Gmail subscribers
- **Kind:** bug · **State:** todo · **Priority:** P2 · **Labels:** prod-incident, unplanned
- **Created:** 2026-11-09 · **Updated:** 2026-11-09 · **Owner:** unassigned
- **Parent:** none · **Due:** none · **Continues / duplicates / blocks:** none

Since about 06:40 UTC today, renewal receipts to Gmail addresses bounce with 550 5.7.26 (unauthenticated sender). Still happening. Log: docs/incidents/2026-11-09-renewal-email-bounces.md.

**Log**
- 2026-11-09 · created
