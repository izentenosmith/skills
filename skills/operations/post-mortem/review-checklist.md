# Review before publishing

**No postmortem is published unreviewed** (*Site Reliability Engineering*, ch. 15). An unreviewed record might as well not exist: the timeline carries errors only the responders can catch, and nobody trusts a record that nobody checked. Review is also where the record gets its status — `draft` until it passes, `reviewed` when it has, `published` once it's circulated.

The reviewer is someone other than the author — ideally one responder and one person who wasn't involved. The author can't do it, for the same reason the author can't proofread their own blame.

## The review

- [ ] **The key evidence was captured.** Every timeline entry has a source tag; the gaps are named (no logs before 14:00, chat export missing). Nothing material is reconstructed from memory without being marked as recollection.
- [ ] **The impact is complete.** Users and records counted as fractions; wrong data included, not just errors; internal cost included; what was still outstanding at resolution stated.
- [ ] **The factors go deep enough.** Every category swept, with "none found" where nothing was; each factor descended to something concrete about the system; the trigger and the latent condition distinguished. A factor that stops at a person's action hasn't been descended.
- [ ] **Responders confirm the timeline.** Each person named in an action has read the entries about them and either confirmed them or had them corrected.
- [ ] **It's blameless and descriptive.** The blamelessness pass holds on the final text: no counterfactuals, no names on mistakes, no "human error", no prescription.
- [ ] **No customer can be identified**, and no secret appears in a quoted log line or screenshot.
- [ ] **The metadata block is filled** with the shared vocabulary, so the record can be counted ([template.md](template.md)).

A failed item goes back to the author with the specific gap. When every item holds, set the status to `reviewed`.

## Where the follow-ups are judged

The SRE review also asks whether the action plan is appropriate. In this collection that judgment belongs to the follow-through, not the record: incident-fix's follow-through step turns each factor into a typed, owned, dated follow-up or an accepted risk, and that list is reviewed there. The reviewer of the record checks only that **every factor is stated clearly enough to be acted on**.

## After publishing

- **Circulate it** — first to everyone involved, then beyond the team. A record read only by its responders has taught the organization nothing.
- **Make it findable** — in the repo's postmortem folder or wherever previous records live, with the same file naming, and linked from the incident's tracker item.
- **Use it again.** Old records are training material: a periodic reading of a past postmortem, or a role-played replay of one where a new responder works the incident from the first alert, builds the response skills an incident needs before the next one arrives.
