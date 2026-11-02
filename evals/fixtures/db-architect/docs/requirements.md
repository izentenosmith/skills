# Relaunch requirements (product, 2026-10-30)

## R1 — On-sales
Big on-sales open at a fixed time. The largest last season peaked at **2,400 seat holds per second for
about eight minutes**; product expects up to **4,000 per second** after the relaunch. Normal traffic is
under 50 holds per second. A hold lasts 10 minutes, then the seat is released unless paid.

## R2 — No seat sold twice
A seat may never be sold to two people, under any failure. This is the one rule product will not trade.

## R3 — Volume
About 2 million seats per season across all venues; 30 million ticket rows after five seasons. Orders
and tickets must be kept seven years (tax).

## R4 — My tickets
Right after paying, the buyer is taken to "My tickets" and must see the ticket they just bought.

## R5 — Payments
The payment provider calls our webhook when a payment succeeds and **retries the call** until it gets a
200, sometimes several times for the same payment. A paid order must never be lost: product's target is
**zero lost paid orders**, even if the main database server fails.

## R6 — Search
Buyers search events by artist, venue and date, with typo tolerance. Search traffic after the relaunch
is not known yet; marketing will have an estimate in January.

## R7 — Sales dashboard
Venue managers get a sales dashboard (sales by event, by hour, by channel). Figures up to **15 minutes
old** are fine.
