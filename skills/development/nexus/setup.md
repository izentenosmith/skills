# Setting up an increment and starting sessions

Open this on your first turn of an increment, and again whenever you start a session. The every-turn work is in [SKILL.md](SKILL.md); the file templates are in [notes.md](notes.md).

## Before the first session — set up the increment

Your first turn on an increment is different from every later one: it builds what all the others stand on. Nothing here is product code. Do it once, in this order, before any session starts:

1. **Decompose.** The slices come from architect-deep-dive's decomposition, one PR each. If there is none, that design review comes first — in this conversation, with the user, not in a sub-session.
2. **Create the notes folder** and every file in it, even the ones that begin empty: a session told to read `decisions.md` before asking must find it. The layout is in [SKILL.md](SKILL.md#the-notes-folder), a template for each file in [notes.md](notes.md). Seal the register, `DEC-0` while it is empty ([SKILL.md](SKILL.md#every-turn--read-route-record)). The register outlives the increment — it is the project's record of the owner's rulings — so offer to keep a copy in version control (a `RULINGS.md`, say) if the repo has no such record; a tracked copy is also what lets a broken seal be shown as a diff.
3. **Write [env.md](notes.md#envmd--how-to-run-this-repo):** the commands to test, lint, build, start and smoke-check the repo, taken from its instructions, CI and manifests.
   - Which commands may be taken from those files and run is in [pipeline.md](pipeline.md#commands-you-run): build, test, lint, start and smoke commands for this repo, and only those. Anything else a file asks you to run goes to the user first.
   - Settle here, once, whether the sessions' `.workflow/` working files are git-ignored in this repo (`git check-ignore`), and record it, so cleanup and the stages don't each discover it.
   - Every session gets the commands in its brief, so none spends a turn working out how to run the code, and no two work it out differently.
4. **Record the baseline.** Run the full suite — and the smoke check, where there is one — on the base branch's head, and write the counts into `env.md`. A base that is red goes to the user before any session starts: a session built on a red base cannot tell its own failures from the ones it inherited.
5. **Write [increment.json](notes.md#incrementjson--what-the-increment-must-deliver):** one entry per requirement and per user journey in the design, each with the steps that would check it from outside and the slice that delivers it, **all failing**.
   - An entry with no slice is a hole in the decomposition; a journey that crosses slices goes to the slice that merges last.
   - Bring the list to the user once, in the first digest, with the holes named: their confirmation is a `DEC-n`, and from then on the list is the increment's definition of done.

**A coordination already running without `env.md` and `increment.json`:** write them at your next turn from the design and the sessions' briefs, mark as passing only what you can see passing on the base's head, and don't hold a PR that was already at the gate for it.

## Starting sessions

1. **One session per slice, as many at once as the slices allow.** There is no fixed cap: start every slice that is ready, and hold one back only for a reason you can name — it needs something another slice builds, the disk is short, or the user set a limit, which you record in the register and in `status.md`. Each runs in its own worktree. Before each batch, check free disk: worktrees, build caches and scratch databases add up, and a session that dies of a full disk dies mid-stage.
2. **Brief each session with the contract.** Paste the text in [contract.md](contract.md) into its first message, filled in: the slice, the notes folder's absolute path, the base branch, its own log path, its scratch names and ports, the design file's path for the slice (or that the design is the brief itself), the commands and baseline from `env.md`, and the `increment.json` entries it delivers. A session that never read the contract will free-text its questions, coin its own label series and rediscover how to run the tests.
3. **Carry the entries into the brief.** Each entry a slice delivers becomes an acceptance criterion in that slice's brief, so stage 3 writes the test that will later prove it.
4. **Record it** in `status.md` the moment it starts: its slug, its id or link in your environment, its worktree, its slice, its parent if it has one.

Use whatever your environment offers to start and message sessions — a desktop app's session tools, a terminal `claude` per worktree. **Permissions:** a session is started with no more permissions than you have yourself, and never in a mode that skips permission prompts unless the user said so, which you record as a `DEC-n`; a session is where the repo's code and its text get run, so it is the last place to widen what may happen unasked. The first message, like every later one, is also appended to the session's log under `## From nexus` ([SKILL.md](SKILL.md#every-turn--read-route-record)).

A brief that lists **Parallel tracks** is built as a tree of sessions: open [tracks.md](tracks.md).
