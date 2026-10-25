# Detection Signals — Reproducible Grep Appendix

> Copy-pasteable commands for the rubric's anti-patterns, each with its **confidence tag**
> (✅ decidable / ⚠️ proxy / 🔬 needs-data — see [`scoring.md`](scoring.md)). Run from the repo root.
> A match is a **candidate**: read the job in context. YAML nesting, `extends:`/anchors, reusable
> workflows and templates mean a line's effect depends on where it's included.
>
> Prefer parsers when present: `actionlint`, `zizmor` (GitHub Actions security), `glab ci lint`,
> `checkov -d . --framework github_actions,gitlab_ci,azure_pipelines`, `shellcheck` on extracted
> scripts, `gitleaks detect`. Grep is the fallback and the triage scan.

## Platform translation

Signals are written for GitHub Actions (GHA) and GitLab CI. The anti-pattern holds elsewhere; the
signal moves.

| Concern | GitHub Actions | GitLab CI | Azure Pipelines | Jenkins | CircleCI |
|---|---|---|---|---|---|
| Files | `.github/workflows/*.yml` | `.gitlab-ci.yml`, `include:` | `azure-pipelines*.yml`, `templates/` | `Jenkinsfile`, shared libraries | `.circleci/config.yml` |
| Stage dependency | `needs:` | `needs:` / `stages:` order | `dependsOn:` | `stage` order | `requires:` |
| Ignore failure | `continue-on-error: true` | `allow_failure: true` | `continueOnError: true` | `catchError`, `returnStatus: true` | `when: always` on next step |
| Retry | `nick-fields/retry`, rerun | `retry:` | `retryCountOnTaskFailure:` | `retry(n)` | `max_auto_reruns` |
| Manual gate | `environment:` with reviewers (UI 🔬) | `when: manual`, protected env | `environment:` approvals (UI 🔬), `ManualValidation@` | `input` | `type: approval` |
| Federated identity | `permissions: id-token: write` + `aws-actions/configure-aws-credentials` with `role-to-assume` / `azure/login` with `client-id` | `id_tokens:` | workload identity federation service connection | plugin-dependent | `oidc` contexts |
| Third-party code | `uses: owner/repo@ref` | `include: remote/project`, `image:` | `resources.repositories`, tasks | plugins, `@Library('x@ref')` | `orbs:` |
| Untrusted trigger | `pull_request_target`, `workflow_run`, `issue_comment` | fork MR pipelines in parent project | PR builds from forks with secrets enabled | multibranch fork PRs | forked builds with secrets |
| Schedule | `on: schedule: cron` | pipeline schedules (UI 🔬), `rules: if $CI_PIPELINE_SOURCE == "schedule"` | `schedules:` | `cron` trigger | `triggers: schedule` |

Set `CI` to the pipeline files once (uses `find`, so it works in bash and zsh alike — a bare glob
that matches nothing aborts the whole `ls` in zsh):

```bash
CI=$(find .github/workflows .circleci -name '*.y*ml' 2>/dev/null; find . -maxdepth 1 \( -name '.gitlab-ci.yml' -o -name 'azure-pipelines*.yml' -o -name 'Jenkinsfile' -o -name 'bitbucket-pipelines.yml' \) 2>/dev/null)
[ -n "$CI" ] || echo "no pipeline files found — stop here: grep with an empty \$CI reads stdin and hangs"
```

Add shared template directories (`templates/`, `.gitlab/ci/`, `vars/` for Jenkins libraries) to `CI`
when the repo has them.

## Inventory

| What | Command |
|---|---|
| Pipelines and triggers | `grep -nE '^on:\|^\s+(push\|pull_request\|pull_request_target\|workflow_run\|workflow_dispatch\|schedule\|release\|issue_comment):' .github/workflows/*.y*ml` |
| Jobs per file | `grep -cE '^  [a-zA-Z0-9_-]+:\s*$' .github/workflows/*.y*ml` |
| Shared templates | `grep -nE 'uses:\s*\./\.github/workflows/\|uses:\s*[^/]+/[^/]+/\.github/workflows/\|^include:\|template:\|@Library' $CI` |
| Environments | `grep -nE 'environment:\s*\S+\|name:\s*(dev\|test\|qa\|staging\|stage\|prod\|production)' $CI` |
| Secrets referenced | `grep -ohE 'secrets\.[A-Z0-9_]+\|\$[A-Z][A-Z0-9_]{3,}' $CI \| sort \| uniq -c \| sort -rn` |

## flow

| Anti-pattern | Command | Conf. |
|---|---|---|
| Build inside deploy jobs | `grep -nE 'docker (build\|buildx build)\|npm run build\|mvn .*package\|gradle .*build\|go build\|dotnet publish' $CI` — then check whether the enclosing job is a deploy job | ✅ |
| Environment-specific build | `grep -nE -- '--build-arg\s+(ENV\|ENVIRONMENT\|STAGE)=\|build:(prod\|staging\|dev)\|-P(prod\|staging)\|NODE_ENV=production .*build' $CI package.json` | ✅ |
| Mutable image tags | `grep -nE ':(latest\|main\|master\|develop\|\$\{?\{?\s*github\.ref_name)' $CI` in push/deploy steps | ✅ |
| Deploy by tag not digest | `grep -nE 'kubectl set image\|helm upgrade\|image:' $CI k8s/ helm/ deploy/ 2>/dev/null \| grep -v '@sha256:'` | ⚠️ |
| Schedule-only stages | `grep -nB2 -A2 'schedule:' $CI` — jobs/workflows with no push/PR trigger | ✅ |
| Long inline scripts | `awk '/run: \|/{f=1;n=0;next} f&&/^\s{6,}/{n++} f&&!/^\s{6,}/{if(n>15)print FILENAME": "n" lines";f=0}' .github/workflows/*.y*ml` | ⚠️ |
| Copy-pasted jobs | `for f in .github/workflows/*.y*ml; do md5 -q <(grep -vE 'name:\|environment:' $f); done \| sort \| uniq -d` (macOS `md5 -q`; Linux `md5sum`) | ⚠️ |
| No dependency cache | `grep -nE 'actions/cache\|cache:\s*(npm\|pip\|yarn\|pnpm\|gradle\|maven)\|cache:\s*$\|--mount=type=cache' $CI` (absence) | ✅ |

## feedback

| Anti-pattern | Command | Conf. |
|---|---|---|
| Silenced failures | `grep -nE 'continue-on-error:\s*true\|allow_failure:\s*true\|continueOnError:\s*true\|\|\|\s*true\b\|-DskipTests\|--passWithNoTests\|--no-verify' $CI` | ✅ (check the job is a test/gate) |
| Retries on tests | `grep -nE 'retry:\|retryCountOnTaskFailure\|nick-fields/retry\|--reruns\|rerunFailingTestsCount\|retries:' $CI pytest.ini pyproject.toml jest.config.* playwright.config.* 2>/dev/null` | ⚠️ |
| Growing skip lists | `grep -rnE '@(Ignore\|Disabled)\b\|\.skip\(\|xit\(\|pytest\.mark\.skip\|t\.Skip\(' --include='*.{java,kt,ts,js,py,go}' . \| wc -l` (compare over history) | ⚠️ |
| Deploy not gated on tests | read `needs:` of every deploy job — no test job in its transitive `needs` | ✅ |
| Reports lost on failure | test report upload steps without `if: always()` / `when: always` | ✅ |
| Sleeps in tests | `grep -rnE '\bsleep\s+[0-9]+\|Thread\.sleep\|time\.sleep\(' tests/ test/ e2e/ 2>/dev/null` | ⚠️ |

## release

| Anti-pattern | Command | Conf. |
|---|---|---|
| Deploy with no post-check | last step of each deploy job is `kubectl apply`/`helm upgrade`/`terraform apply`/`az .* deploy`/`aws .* deploy` with no `rollout status`, `--wait`, `--atomic`, health `curl`, or smoke job after it | ✅ |
| Helm without atomic/wait | `grep -nE 'helm upgrade' $CI \| grep -vE -- '--atomic\|--wait'` | ✅ |
| No rollback job | `grep -nEi 'rollback\|rollout undo\|helm rollback\|swap' $CI` (absence) | ✅ |
| Different deploy per env | `ls scripts/ ci/ deploy/ 2>/dev/null \| grep -Ei 'deploy[-_](prod\|production\|staging)'`; diff deploy jobs | ✅ |
| Big-bang strategy | `grep -rnE 'maxUnavailable:\s*(100%\|[0-9]{2,}%)\|strategy:\s*\n\s*type:\s*Recreate\|type:\s*Recreate' k8s/ helm/ charts/ deploy/ 2>/dev/null` | ✅ |
| Canary without analysis | `grep -rnE 'kind:\s*Rollout\|canary' k8s/ helm/ charts/ deploy/ $CI 2>/dev/null` then look for `analysis:` / metric checks | ✅ |
| Skip-tests hotfix | `grep -nEi 'skip[_-]?tests\|\[skip ci\]\|hotfix' $CI` | ✅ |
| Migrations | `ls -d migrations db/migrate alembic flyway liquibase prisma/migrations 2>/dev/null`; `grep -nE 'migrate\|flyway\|liquibase\|alembic upgrade' $CI` | ✅ structure |
| Destructive DDL in a release | `git diff <base> -- '*.sql' '**/migrations/**' \| grep -iE '^\+.*(drop (table\|column)\|rename (column\|to)\|alter column .* type)'` | ⚠️ |
| Manual gates everywhere | `grep -nE 'when:\s*manual\|ManualValidation@\|type:\s*approval\|\binput\s*\(' $CI` — count per environment | ⚠️ |
| Deploy markers | `grep -nEi 'annotation\|deployment marker\|datadog.*event\|grafana.*annotat\|newrelic.*deployment\|sentry-cli releases' $CI` (absence) | ✅ |

## security

| Anti-pattern | Command | Conf. |
|---|---|---|
| Secret literals | `gitleaks detect --no-git -s .` or `grep -nE 'AKIA[0-9A-Z]{16}\|ghp_[A-Za-z0-9]{36}\|glpat-[A-Za-z0-9_-]{20}\|xox[bap]-\|-----BEGIN (RSA\|OPENSSH\|EC) PRIVATE KEY' -r .` | ✅ |
| Secrets echoed | `grep -nE 'echo\s+.*\$\{\{\s*secrets\.\|echo\s+\$[A-Z_]*(TOKEN\|SECRET\|PASSWORD\|KEY)' $CI` | ✅ |
| `pull_request_target` + PR checkout | `grep -lE 'pull_request_target\|workflow_run' .github/workflows/* \| xargs grep -nE 'ref:\s*\$\{\{\s*github\.event\.(pull_request\.head\|workflow_run\.head)'` | ✅ |
| Script injection | `grep -nE 'run:.*\$\{\{\s*github\.(event\.(issue\|pull_request\|comment\|review\|head_commit\|commits)\|head_ref)' .github/workflows/*` (multi-line `run: \|` blocks need `zizmor`) | ✅ |
| Write-all / missing permissions | `grep -nE 'permissions:\s*write-all' .github/workflows/*`; files without any `permissions:` → `grep -L 'permissions:' .github/workflows/*` | ✅ (🔬 repo default) |
| Static cloud keys | `grep -nE 'AWS_SECRET_ACCESS_KEY\|AZURE_CLIENT_SECRET\|GOOGLE_CREDENTIALS\|GCP_SA_KEY\|ARM_CLIENT_SECRET' $CI` | ✅ |
| OIDC in use | `grep -nE 'id-token:\s*write\|id_tokens:\|role-to-assume\|workload_identity_provider\|client-id:' $CI` | ✅ (presence = 🟢) |
| Unpinned actions | `grep -nE 'uses:\s*[^./][^@]+@' .github/workflows/* \| grep -vE '@[0-9a-f]{40}\b'` | ✅ |
| Unpinned images | `grep -nE '^\s*(image\|container):\s*\S+' $CI \| grep -vE '@sha256:' \| grep -E ':latest\|:[a-z]+$\|image:\s*[^:]+$'` | ✅ |
| Remote includes without ref | `grep -nA2 -E 'include:' .gitlab-ci.yml \| grep -E 'remote:\|project:' ` then check `ref:` | ✅ |
| Self-hosted on public PRs | `grep -nE 'runs-on:.*self-hosted' .github/workflows/*` in workflows triggered by `pull_request` from forks | ⚠️ (🔬 repo visibility/settings) |
| Scanning present | `grep -nEi 'codeql\|semgrep\|sonar\|snyk\|trivy\|grype\|dependency-check\|dependabot\|renovate\|gitleaks\|trufflehog\|checkov\|tfsec\|zizmor' $CI .github/dependabot.yml renovate.json 2>/dev/null` | ✅ (absence = 🔴) |
| Signing / provenance | `grep -nEi 'cosign\|sigstore\|attest-build-provenance\|slsa\|syft\|sbom' $CI` | ✅ |

## environments

| Anti-pattern | Command | Conf. |
|---|---|---|
| Config-path fast lanes | `grep -nE 'paths(-ignore)?:\|changes:' -A4 $CI \| grep -Ei 'config\|\.ya?ml\|values\|flags'` — then check what those paths skip | ⚠️ |
| Runtime parity | compare `FROM`, `node-version`, `python-version`, `java-version`, `image:` across environment jobs and Dockerfiles | ⚠️ |
| Prod data restores | `grep -nEi 'pg_restore\|pg_dump\|mysqldump\|mongorestore\|restore.*(prod\|production)\|snapshot.*prod' $CI scripts/ 2>/dev/null` | ✅ then read for masking |
| Env IaC presence | `ls -d infra terraform envs live environments 2>/dev/null` and look for each environment named in the pipeline | ✅ |

## infrastructure

| Anti-pattern | Command | Conf. |
|---|---|---|
| Apply without saved plan | `grep -nE 'terraform\s+apply' $CI \| grep -vE 'apply\s+(-input=false\s+)?\S+\.(tfplan\|plan\|out)\b\|apply\s+.*\$\{?\w*[Pp][Ll][Aa][Nn]'` | ⚠️ (read the command) |
| `-auto-approve` | `grep -nE 'apply.*-auto-approve' $CI` | ⚠️ (fine when applying a saved plan) |
| Plan on PR | `grep -lE 'terraform plan\|tofu plan\|atlantis\|tfcmt\|terraform-plan' $CI` in PR-triggered workflows | ✅ |
| Concurrency | `grep -nE '^concurrency:\|^\s+concurrency:\|resource_group:\|lockBehavior:' $CI` (absence near apply jobs) | ✅ |
| Drift schedule | workflows with `schedule:` that run `plan -detailed-exitcode` | ✅ |
| Destroy guard | `grep -nE 'show -json.*\|.*jq.*(delete\|destroy)\|resource_changes.*delete\|conftest\|opa eval' $CI` | ✅ |
| One identity for all envs | the same `role-to-assume`/service connection/secret name used by plan and apply and by every environment | ✅ |
