# Decisions — the user's, verbatim

## DEC-1: No administrator override in increment 3
**Decided:** 2026-11-12 by Marta · **Asked by:** the nexus · **Applies to:** all sessions
**Question:** Should any of the new booking rules be overridable by a venue administrator in this increment?
**Answer:** "No overrides this time. If a venue needs an exception they call us. We can look at it again in the spring."
**Means:** no slice builds an override, a bypass flag or an admin path around a rule.
**Supersedes:** —

## DEC-2: Slot times are venue-local; no time-zone work
**Decided:** 2026-11-12 by Marta · **Asked by:** hours-holidays · **Applies to:** all sessions
**Question:** Slots are stored as naive datetimes. Do the new rules convert them to UTC or to the guest's time zone?
**Answer:** "Leave them as they are. A slot is in the venue's own time and so is 'now' for these rules. Time zones are a separate project."
**Means:** every rule compares naive venue-local datetimes; no slice adds a time-zone conversion.
**Supersedes:** —

## DEC-3: New rules apply to new submissions only
**Decided:** 2026-11-14 by Marta · **Asked by:** party-limits · **Applies to:** all sessions
**Question:** When a new rule ships, do bookings already in the store get checked against it and cancelled if they fail?
**Answer:** "No. Whatever is already booked stays booked. The new rules are for bookings made after we ship, and nobody runs anything over the old ones."
**Means:** no slice re-validates, backfills or cancels stored bookings; a rule is applied at submission and nowhere else.
**Supersedes:** —
