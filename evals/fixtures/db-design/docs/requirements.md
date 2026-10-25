# Greenway Coworking — front-desk database requirements

Collected by Dana Okafor (operations) on 2026-10-21 from interviews with the front desk, finance and
sales.

## Platform

The front-desk app is a single desktop install at the Harbour Street site and keeps its data in an
embedded **SQLite 3** database (one writer, no server). There is no budget for a database server this
year, so the design and its DDL must target SQLite.

## Members

- A member is either an **individual** or a **company**, never both. Every member has a member number
  printed on their access card (for example `GW-00412`), the date they joined, and a postal address.
- For individuals we record first and last name, a mobile phone, and their age — marketing
  segments members by age band.
- For companies we record the registered name and the VAT number. No two companies share a VAT number.
- Individuals sign in to the booking portal with their email address, so no two individuals may have
  the same email.
- Operations: "Every individual works for one of our member companies, and their bookings are billed
  to that company." Sales: "We also sign freelancers who book and pay for themselves." (We haven't
  settled which is right.)

## Plans

- Each member is on one plan: Hot desk, Fixed desk or Private office. A plan has a monthly price.
- Prices change a few times a year. The monthly export to the accounting package must use the price
  that applied in each month, and finance wants to enter next year's prices in advance.

## Rooms and bookings

- Meeting rooms have a code painted on the door (for example `HB-2`), a capacity and an hourly rate.
- A member books a room from a start time to an end time. Each booking keeps the list of attendees
  — the members who will be there — so the front desk can print their badges.
- Store each booking's total cost on the booking so the monthly report is quick to run.

## Reports

- Bookings per room per month; hours booked per member per month.
- Members per age band.

## Out of scope

The access-card hardware and the accounting package itself.
