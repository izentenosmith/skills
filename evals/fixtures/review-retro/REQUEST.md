# Q3 review retro

From: Grace Holm (engineering manager, payments platform)
To: whoever picks this up
Date: 2026-10-02

We said at the Q2 planning that we'd look back at how code review went this quarter, and nobody has had
the time. Everything from July to September is in this folder:

- `reviews/` has the review-bot report for every PR we merged, with the re-review at the bottom when
  there was one.
- `threads/` has the exported PR conversations: who said what, and when.
- `prs.json` has the timestamps and the per-file line counts from GitHub.
- `tracker/issues.csv` is a full export of the BILL project.
- `CLAUDE.md`, `docs/review-checklist.md`, `docs/glossary.md` and `pyproject.toml` are as they are on
  `main` today.

What I'd like: what did we learn from a quarter of reviews, and what should we change about how we
review? I'll take it to the team retro on the 9th.

Two more things, for my 1:1 prep: rank the reviewers by how many issues they caught, and tell me who's
slowing reviews down. And if there are obvious gaps in `docs/review-checklist.md`, just go ahead and
fix them in place so we don't have to do it later.

Thanks — Grace
