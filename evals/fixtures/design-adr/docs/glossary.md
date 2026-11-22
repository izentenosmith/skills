# Glossary

**Account** — the venue group that holds the contract with us and owns one or more venues. Rule settings belong to it. _Avoid:_ customer, tenant, client.

**Venue** — one restaurant or bar, belonging to exactly one account. _Avoid:_ site, location, outlet.

**Slot** — the start time a booking is for, at a venue. _Avoid:_ reservation time, booking time, seating.

**Booking** — a request for a party to be seated at a venue's slot, accepted or refused when it is submitted. _Avoid:_ reservation, order.

**Rule** — one constraint a booking must satisfy to be accepted. _Avoid:_ validator, check, policy.

**Violation code** — the upper-case string a rule returns when a booking breaks it, such as `PARTY_TOO_LARGE`. _Avoid:_ error, reason, failure.
