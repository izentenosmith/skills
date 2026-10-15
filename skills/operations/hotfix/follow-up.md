# The follow-up item

What a band-aid owes, and where every non-blocking review finding goes. **An item with no date is a wish**, and an item nobody can find is the same as none.

## When one is owed

- The fix **guards a symptom** instead of removing the cause — a clamp, retry, default, special case, catch, or disabled path.
- The review pass found something **real but not blocking**.
- The repo had **no test for this area** and you wrote a minimal check rather than a proper test.
- The caller sweep found **duplicated logic** you fixed in one place but couldn't safely unify now.

## The item

```markdown
### Follow-up: <the proper fix, as an outcome — "invoice totals are computed once from unrounded line amounts">
- **Origin:** hotfix <slug> at <commit sha>, <UTC date>
- **Why it wasn't done now:** <the honest reason — time, risk, needed a design decision, out of the lane's scope>
- **What's in place meanwhile:** <the band-aid, and what it does not cover>
- **Done looks like:** <an observable behavior, verifiable through a public interface>
- **Target date:** <date>
- **Owner:** <a person or team, or "unassigned — needs an owner" said plainly>
```

## Where it goes

- **A tracker exists** (found from evidence in discovery): create the item there — **after the user confirms** — using the team's labels and conventions. Put its id in the commit message the way the repo's commits already reference tickets.
- **No tracker**: append it to `.workflow/follow-ups.md` and commit that file with the fix, so the item travels with the code that owes it. Reference it in the commit message as `follow-up: .workflow/follow-ups.md#<heading>`.

Either way, the final checklist names the item.
