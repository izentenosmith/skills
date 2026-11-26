Answer key for `ci-forks/`. It lives **outside** the fixture folder on purpose.

# ci-forks — `pipelines`, fixing a repo before it opens to fork PRs (eval 80)

A static docs site with three GitHub Actions workflows. The repo goes public next week; most docs PRs
will come from forks, and the docs team reviews from the per-PR Cloudflare preview. The prompt asks for
the workflows to be fixed in place, keeping fork previews working.

| # | In the fixture | Real or decoy | Why |
|---|---|---|---|
| 1 | `ci.yml` (`pull_request`) builds the PR and uploads artifact `preview` (`dist/` + `pr/number`); `preview-deploy.yml` (`workflow_run`, `CLOUDFLARE_API_TOKEN`, `pull-requests: write`) checks out `main`, runs `npm ci`, then **downloads the artifact with no `path:`**, i.e. into the workspace root, and then runs `npx wrangler …` and `node scripts/comment-preview.mjs` | **Real — Critical** | On a fork PR, `ci.yml` runs *as the fork wrote it*, so the artifact can hold anything: `scripts/comment-preview.mjs`, `node_modules/.bin/wrangler`, `node_modules/wrangler/…`. Extracted over the checkout, the next two steps run the attacker's code in the job that holds the Cloudflare token and a write token. The header comment ("we never check out the pull request… safe for forks") is the lure: true, and beside the point. |
| 2 | `pr/number` read from the artifact and checked against `^[0-9]+$` before use | decoy — safe | the untrusted value is validated before it reaches a shell or an output |
| 3 | `echo "${{ github.event.pull_request.number }}"` in `ci.yml` | decoy — safe | a number, in a `pull_request` job with a read-only token and no secrets |
| 4 | `triage.yml` on `pull_request_target` with `pull-requests: write` | decoy — safe | nothing from the PR is checked out or run; `actions/labeler` reads the diff through the API; the title reaches the shell through `env:`, not `${{ }}` in `run:`. Moving it to `pull_request` breaks labels on fork PRs. |
| 5 | every action pinned by full SHA; `persist-credentials: false`; top-level least-privilege `permissions` | done well | keep |

**The fix** (any of these closes #1): download the artifact **outside the workspace** (`path: ${{ runner.temp }}/preview`) and deploy `$RUNNER_TEMP/preview/dist`, reading `pr/number` from there; or into a dedicated subfolder that nothing executes from. Restricting the deploy to same-repo PRs (`head_repository == github.repository`) closes the hole but drops fork previews, which the prompt forbids. Moving the deploy to `pull_request_target` with a head checkout is the pwn request.

**Why a bare agent plausibly misses it:** `preview-deploy.yml` reads as hardened (SHA pins, `persist-credentials: false`, `--ignore-scripts`, a validated PR number, a comment explaining why it is safe), and the risky-looking `pull_request_target` sits in `triage.yml`. The defect is an *omitted* `path:` whose default only matters once you trace which trigger wrote the artifact — the pipelines skill's R1 asks for exactly that trace (every credential a job can reach, and which triggers can reach that job), and its rubric names `workflow_run` as an untrusted trigger.
