# marketplace

This repo is the source; a marketplace listing is a build artefact made from it. [`agensi.py`](agensi.py) turns each skill under `skills/` into a zip that stands alone on [Agensi](https://www.agensi.io), where someone may install one skill and none of its neighbours, and each bundle in [`bundles.json`](bundles.json) into one zip of several skills.

```bash
python3 marketplace/agensi.py                             # every skill and bundle → dist/agensi/<name>.zip
python3 marketplace/agensi.py appsec incident-response    # just these
python3 marketplace/agensi.py --check                     # build and check, write nothing (CI runs this)
```

## Pricing

**$5 a skill, $10 a bundle.** A single skill lists at $5 one-time; a bundle lists at a flat $10 one-time, however many skills it holds — `incident-response` (three skills) and `infrastructure-delivery` (two) are both $10. The prices are `SKILL_PRICE_USD` and `BUNDLE_PRICE_USD` in `agensi.py`; each run prints the price per listing and records it in `manifest.json`. Agensi keeps 30%: a $5 sale pays $3.50.

## Bundles

```json
{ "incident-response": ["hotfix", "incident-fix", "post-mortem"] }
```

A bundle zips its skills' folders side by side (`hotfix/SKILL.md`, `incident-fix/SKILL.md`, …). Links between members stay live as `../<member>/<file>`; links to skills outside the bundle become names, as for a single skill. A bundle's name may not be a skill's, and it needs two or more skills that exist.

Not yet confirmed: whether Agensi's submit form takes a zip with several `SKILL.md` files as one listing. A single-skill zip with the `<name>/SKILL.md` layout is confirmed.

## The update loop

1. Change a skill here, as usual.
2. Run `python3 marketplace/agensi.py`. The table marks each listing **new**, **changed** or **unchanged** against `dist/agensi/manifest.json` from the previous run. Zips are reproducible, so an unchanged listing gives the same bytes.
3. Re-upload the **changed** zips from the Creator Dashboard.

`dist/` is ignored by git; keep the folder between runs, or the next run marks everything new.

## What a package changes

Only the copy in the zip; the repo stays as it is.

| In the repo | In the zip |
|---|---|
| A symlinked reference doc | The file itself |
| A link to another skill's reference doc | That doc, copied in (with whatever it links to), and the link pointing at the copy — or, in a bundle that holds that skill, a live `../<skill>/<file>` link |
| A link to another skill's `SKILL.md` | The skill's name in plain text, plus a **Related skills** section in `SKILL.md` naming them as separate, optional skills — or a live link, inside a bundle |
| A link to anything else outside the skill — a family README, the harness | The link text |
| Text listed in [`patches.json`](patches.json) | The replacement |

`patches.json` holds the edits a rule can't make — a sentence about the harness, a sample value a secret scanner would flag. Each `old` must match exactly once; when the source changes and a patch stops matching, the build fails and says which one, so a stale patch never silently ships the original text.

```json
{ "<skill>": { "<file in the skill>": [ { "old": "exact text", "new": "replacement" },
                                       { "drop_section": "## Under the PR harness" } ] } }
```

`drop_section` removes the section under that exact heading line, up to the next heading of the same or a higher level (headings inside code fences don't count), and the `---` left dangling above it when it was the last section. The review family's `## Under the PR harness` sections go this way: each is the contract `harness/prreview.py` calls the skill under, which no buyer has. code-xray keeps its section, because the JSON reference in it also documents `xray.py pr --json`. A heading that no longer matches exactly once fails the build, like a stale `old`.

## What it checks

A problem fails the run and nothing is written:

- frontmatter: `name` matches the folder, lowercase letters, digits and hyphens, ≤64, no "anthropic" or "claude"; `description` 1–1024 characters, no XML tags
- every relative link resolves to a file inside the zip
- nothing that looks like a live key or token (OpenAI-style, AWS, GitHub, GitLab, Slack, a private key block); a detection regex such as `AKIA[0-9A-Z]{16}` is not one
- the zip is under Agensi's 50 MB limit
- every patch applies and names a skill that exists; every bundle names skills that exist

Mentions of "the harness", which no zip ships, are listed as warnings: a sentence like "if the repo carries the harness, run…" is fine without it, and the list shows where a skill may lean on it harder. The networking skills ship their own `scripts/netgraph.py` instead, so netaudit's one optional mention is all that family shows. The development family's `harness/ledger.py` self-checks and the review family's harness contracts are patched out, so what remains are optional one-liners (and hotfix's "follow-up for the harness", which means a test harness).

Descriptions within 24 characters of the 1024 limit are listed too: still valid, but the next sentence added to one fails the build.

Tests: `python3 -m unittest discover marketplace/tests`.

## Submitting on Agensi

What the submit form at `agensi.io/dashboard/submit` does, as of the first listing (Post-Mortem, November 2026):

- **The zip.** Up to 50 MB. It reads the frontmatter and fills in the name (as words — `post mortem`), and saves a draft at once; every later change autosaves.
- **It auto-fills almost everything else with AI**, and the text needs reading before it ships:
  - *Summary* and *full description* — usually close; replace them with your own copy.
  - *Demo* — **the request and the result are invented**: a plausible session about a system that doesn't exist. Use **Clear suggested demo**, then paste a real run (below).
  - *Categories* (up to 3; the first is the marketplace page the listing lives on) and *tags* — often wrong for the domain. Picking categories rewrites the category tags.
  - *Use cases*, *known limitations*, *FAQ* — mostly accurate; check for the skill's name in lowercase words and for "purchase" wording on a free listing.
  - *Permissions* — required tools from the files (`Git`), and "Tools used" checkboxes: Terminal / Shell, Read Files, Write Files, Browser, Network Access, Environment Variables. Tick what the skill actually does; the detector under-ticks (a skill that runs `git log` and writes a document needs Terminal and Write Files too).
- **Fields and limits.** Name ≤ 60 characters · summary ≤ 300 · full description in Markdown · demo result "700+ characters", the complete output · pricing Free / One-time (minimum $1) / Subscription · logo square 512×512, ≤ 5 MB · up to 6 screenshots, ≤ 10 MB each · optional demo video (YouTube or Loom) and documentation link.
- **Review.** **Submit for review** opens a last checklist — confirm you reviewed the auto-filled fields, the permissions and the pricing — then "Skill submitted!": an automated security scan and admin review, with a notification in 24–48 hours.

### A real demo

The demo is the listing's largest conversion driver, and it should be a real run. The evals already have one per skill: run the skill's eval and paste its `response.md`.

```bash
./evals/setup.sh                                              # once: builds fixture histories
python3 evals/run.py --evals 7 --reps 1 --baseline-ref none   # post-mortem's eval
```

The request is the eval's `prompt` in [`evals/evals.json`](../evals/evals.json); the result is the run's `outputs/response.md`. Say in the demo that the system is a seeded test incident, not a customer's.

To paste a long output, copy it as UTF-8: `LC_ALL=en_US.UTF-8 pbcopy < response.md`. Without a UTF-8 locale, macOS's `pbcopy` reads the bytes as Mac Roman, and every `→`, `–` and `—` lands on the listing as `‚Üí`, `‚Äì`, `‚Äî`.

A listing under review can still be edited from **Creator Studio → Skills → ✎**. Metadata changes such as the demo go live on save; replacing the zip needs re-approval.
