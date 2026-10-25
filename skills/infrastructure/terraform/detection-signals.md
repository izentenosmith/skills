# Detection Signals — Reproducible Grep Appendix

> Copy-pasteable commands for the rubric's anti-patterns, each with its **confidence tag**
> (✅ decidable / ⚠️ proxy / 🔬 needs-data — see [`scoring.md`](scoring.md)). Run from the codebase
> root. A match is a **candidate**: read the block in context before recording a finding. HCL is
> nested; one-line grep can't tell an `ingress` from an `egress` or see a variable's final value.
>
> Prefer real tools when present — they parse HCL: `terraform fmt -check -recursive`,
> `terraform validate`, `tflint --recursive` (with the provider ruleset), `checkov -d .`,
> `trivy config .`, `gitleaks detect`. Grep is the fallback and the triage scan.

## Platform notes

Signals are written for Terraform + AWS. On other providers the anti-pattern holds; the signal moves.

| Concern | AWS | azurerm | google |
|---|---|---|---|
| Static provider credential | `access_key`, `secret_key` | `client_secret` | `credentials = file(...)` / JSON key |
| Wildcard permission | `"Action": "*"`, `actions = ["*"]` | `actions = ["*"]` in a role definition; `Owner` assignment | `roles/owner`, `roles/editor` bindings |
| Public data store | `acl = "public-read"`, missing `aws_s3_bucket_public_access_block`, `publicly_accessible = true` | `public_network_access_enabled = true`, `allow_nested_items_to_be_public = true` | `allUsers` / `allAuthenticatedUsers` members |
| Destroy protection | `deletion_protection`, `skip_final_snapshot`, `force_destroy` | `prevent_deletion_if_contains_resources`, resource locks | `deletion_protection`, `force_destroy` |
| Backend locking | `use_lockfile`, `dynamodb_table` | azurerm backend locks by blob lease (built in) | gcs backend locks natively |
| Default tags | provider `default_tags {}` | no provider default — tags per resource or policy | provider `default_labels` |

## Inventory

| What | Command |
|---|---|
| Roots (have a backend or cloud block) | `grep -rlE '^\s*(backend\s+"\|cloud\s*\{)' --include='*.tf' . \| xargs -n1 dirname \| sort -u` |
| Child modules called | `grep -rhoE 'source\s*=\s*"[^"]+"' --include='*.tf' . \| sort \| uniq -c \| sort -rn` |
| Resources per directory | `grep -rcE '^resource\s+"' --include='*.tf' . \| awk -F: '{split($1,p,"/"); d=$1; sub(/\/[^/]+$/,"",d); c[d]+=$2} END{for(k in c) print c[k], k}' \| sort -rn` |
| Providers in use | `grep -rhoE '^\s*source\s*=\s*"[a-z0-9-]+/[a-z0-9-]+"' --include='*.tf' . \| sort \| uniq -c` |
| Wrappers present | `find . -maxdepth 3 \( -name terragrunt.hcl -o -name atlantis.yaml -o -name .terraform-version -o -name .tool-versions -o -name .terraform-docs.yml \) -not -path '*/.terraform/*'` |

## structure

| Anti-pattern | Command | Conf. |
|---|---|---|
| Provider configured in a child module | `grep -rnE '^provider\s+"' --include='*.tf' modules/` | ✅ |
| Variables without type | `tflint --recursive --enable-rule=terraform_typed_variables`; by hand, read each `variable` block (multi-line, so grep can't decide it) | ✅ |
| Variables without description | `tflint --enable-rule=terraform_documented_variables` | ✅ |
| Output echoing an input | `grep -rnE 'value\s*=\s*var\.' --include='outputs.tf' .` | ✅ |
| Imperative provisioning | `grep -rnE 'provisioner\s+"(local-exec\|remote-exec)"\|resource\s+"null_resource"\|data\s+"external"' --include='*.tf' .` | ✅ presence, ⚠️ "a resource could do it" |
| Environment-shaped conditionals | `grep -rnE '(var\.env(ironment)?\|terraform\.workspace)\s*==\s*"(prod\|production\|dev\|staging)"' --include='*.tf' .` | ⚠️ |
| Copy-pasted environments | `diff -rq envs/dev envs/prod` then `diff envs/dev/main.tf envs/prod/main.tf` — resource blocks (not values) differing or duplicated | ✅ once diffed |
| Single-resource modules | `for d in modules/*/; do echo "$(grep -hcE '^resource\s+"' $d*.tf 2>/dev/null \| paste -sd+ \| bc) $d"; done \| sort -n \| head` | ✅ (count = 1) |

## state

| Anti-pattern | Command | Conf. |
|---|---|---|
| State tracked in git | `git ls-files \| grep -E '\.tfstate(\.backup)?$'` | ✅ |
| `.gitignore` missing state/.terraform | `grep -nE 'tfstate\|\.terraform/' .gitignore` (absence) | ✅ |
| Roots with no backend | compare the roots list to `grep -rlE 'backend\s+"\|cloud\s*\{'`; any root with `.tf` resources and no match | ✅ |
| Local backend | `grep -rnE 'backend\s+"local"' --include='*.tf' .` | ✅ |
| S3 backend without locking | `grep -rnA12 -E 'backend\s+"s3"' --include='*.tf' . \| grep -cE 'use_lockfile\|dynamodb_table'` per block (0 = no lock) | ✅ |
| DynamoDB-only lock (deprecated) | `grep -rnE 'dynamodb_table\s*=' --include='*.tf' .` without `use_lockfile` | ✅ (Low) |
| Unencrypted S3 state | `grep -rnA12 -E 'backend\s+"s3"' --include='*.tf' . \| grep -nE 'encrypt\s*=\s*false'`; absence of `encrypt` | ✅ |
| Workspace-switched environments | `grep -rnE 'terraform\.workspace' --include='*.tf' .` | ⚠️ (read how it's used) |
| Remote-state fan-in | `grep -rnE 'data\s+"terraform_remote_state"' --include='*.tf' . \| cut -d: -f1 \| xargs -n1 dirname \| sort \| uniq -c \| sort -rn` | ⚠️ |
| Apply chains in scripts | `grep -rnE 'terraform (apply\|output)' --include='*.sh' --include='Makefile' .` | ⚠️ |

## dependencies

| Anti-pattern | Command | Conf. |
|---|---|---|
| No `required_version` (per root) | roots list minus `grep -rlE 'required_version\s*=' --include='*.tf' .` | ✅ |
| Provider without version | `tflint --recursive --enable-rule=terraform_required_providers`; by hand, read every `required_providers` block for entries with `source` and no `version` | ✅ |
| No `required_providers` at all | modules list minus `grep -rlE 'required_providers' --include='*.tf' .` | ✅ |
| Lockfile not committed | `for r in <roots>; do git ls-files --error-unmatch $r/.terraform.lock.hcl >/dev/null 2>&1 \|\| echo "missing: $r"; done`; `grep -n 'terraform.lock.hcl' .gitignore` | ✅ |
| Git module without ref | `grep -rnE 'source\s*=\s*"git(::\|@\|hub\.com)[^"]*"' --include='*.tf' . \| grep -v 'ref='` | ✅ |
| Git module on a branch | `grep -rnE 'source\s*=\s*"[^"]*\?ref=(main\|master\|develop\|dev\|production\|prod\|HEAD)"' --include='*.tf' .` | ✅ |
| Registry module without version | `grep -rnA3 -E 'source\s*=\s*"[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+"' --include='*.tf' . \| grep -c 'version'` per block (0 = unpinned) | ✅ |

## security

| Anti-pattern | Command | Conf. |
|---|---|---|
| AWS access key literal | `grep -rnE 'AKIA[0-9A-Z]{16}\|ASIA[0-9A-Z]{16}' .` | ✅ |
| Provider static credentials | `grep -rnE '^\s*(access_key\|secret_key\|client_secret\|token)\s*=\s*"' --include='*.tf' --include='*.tfvars' .` | ✅ |
| Secret-looking literals | `grep -rnEi '(password\|passwd\|secret\|token\|api_key\|private_key)\s*=\s*"[^"$]{6,}"' --include='*.tf' --include='*.tfvars' .` | ⚠️ then ✅ |
| Secret variables not sensitive | `grep -rnA6 -Ei 'variable\s+"[^"]*(password\|secret\|token\|key)[^"]*"' --include='*.tf' . \| grep -L 'sensitive'` — or read each block | ⚠️ |
| Wildcard IAM | `grep -rnE '"Action"\s*:\s*"\*"\|actions\s*=\s*\["\*"\]\|"Resource"\s*:\s*"\*"\|resources\s*=\s*\["\*"\]\|AdministratorAccess' --include='*.tf' --include='*.json' .` | ✅ (read effect and actions) |
| Static keys for automation | `grep -rnE 'resource\s+"aws_iam_access_key"' --include='*.tf' .` | ✅ |
| Open ingress | `grep -rnE 'cidr_blocks\s*=\s*\["0\.0\.0\.0/0"\]\|ipv6_cidr_blocks\s*=\s*\["::/0"\]\|cidr_ipv4\s*=\s*"0\.0\.0\.0/0"' --include='*.tf' .` | ⚠️ (direction, ports) |
| Public buckets / DBs | `grep -rnE 'acl\s*=\s*"public-read\|publicly_accessible\s*=\s*true\|block_public_acls\s*=\s*false' --include='*.tf' .` | ✅ |
| Unencrypted storage | `grep -rnE 'encrypted\s*=\s*false\|storage_encrypted\s*=\s*false\|kms_key_id\s*=\s*""' --include='*.tf' .` | ✅ |
| No default tags | `grep -rnE 'default_tags\s*\{' --include='*.tf' .` (absence per AWS provider) | ✅ |
| Fail-open module defaults | `grep -rnA4 -E '^variable' --include='*.tf' modules/ \| grep -E 'default\s*=\s*(true\|\["0\.0\.0\.0/0"\]\|"public)'` then read the variable's purpose | ⚠️ |
| Inline SG rules | `grep -rnE '^\s*(ingress\|egress)\s*\{' --include='*.tf' .` inside `aws_security_group` | ✅ |

## change-safety

| Anti-pattern | Command | Conf. |
|---|---|---|
| Index-keyed collections | `grep -rnE '\[count\.index\]' --include='*.tf' .` — then check the resource type is long-lived/stateful | ✅ |
| Unprotected stateful resources | `grep -rnE 'resource\s+"aws_(db_instance\|rds_cluster\|dynamodb_table\|s3_bucket\|kms_key\|route53_zone\|efs_file_system\|ebs_volume\|elasticache_replication_group\|opensearch_domain)"' --include='*.tf' .` then check each for `prevent_destroy` / `deletion_protection` | ✅ |
| Destructive flags | `grep -rnE 'force_destroy\s*=\s*true\|skip_final_snapshot\s*=\s*true\|deletion_protection\s*=\s*false' --include='*.tf' .` | ✅ |
| `ignore_changes = all` | `grep -rnE 'ignore_changes\s*=\s*all' --include='*.tf' .` | ✅ |
| `ignore_changes` on security attributes | `grep -rnA2 -E 'ignore_changes' --include='*.tf' . \| grep -Ei 'policy\|ingress\|egress\|encrypt\|kms\|acl'` | ✅ |
| Data-source fan-out | `grep -rnE '(for_each\|count)\s*=\s*.*data\.' --include='*.tf' .` | ⚠️ |
| Routine `-target` / unsaved plans | `grep -rnE 'terraform\s+apply[^\n]*(-target\|-auto-approve)' .github .gitlab-ci.yml azure-pipelines*.yml Jenkinsfile Makefile *.sh 2>/dev/null` | ✅ |
| Renames without `moved` (PR) | `git diff <base> -- '*.tf' \| grep -E '^[-+]resource\s+"'` — pair removed/added addresses; check for `moved {` | ✅ in a diff |
| `state mv` in docs | `grep -rnE 'terraform state (mv\|rm)' --include='*.md' --include='*.sh' .` | ⚠️ |

## delivery

| Anti-pattern | Command | Conf. |
|---|---|---|
| CI files present (set `CI` for the rows below) | `CI=$(find .github/workflows -name '*.y*ml' 2>/dev/null; find . -maxdepth 1 \( -name '.gitlab-ci.yml' -o -name 'azure-pipelines*.yml' -o -name Jenkinsfile -o -name atlantis.yaml \))` — if empty, skip the rows below (grep with no file reads stdin) | — |
| No static checks in CI | `grep -rlE 'terraform fmt\|terraform validate\|tflint\|checkov\|tfsec\|trivy' <ci files> .pre-commit-config.yaml` (absence) | ✅ |
| Scanner soft-failing | `grep -rnE 'soft_fail\|continue-on-error:\s*true\|allow_failure:\s*true\|--soft-fail' <ci files>` near a scanner | ✅ |
| Apply without saved plan | `grep -rnE 'terraform\s+apply' <ci files> \| grep -vE 'apply\s+[^-]\S*\.(tfplan\|plan)\|apply\s+"?\$\{?\w*plan'` | ⚠️ |
| Laptop applies in docs | `grep -rnE 'terraform apply' --include='*.md' .` | ⚠️ |
| Module tests | `find . -name '*.tftest.hcl' -o -path '*/test/*_test.go' -o -type d -name examples` | ✅ |
| Drift schedule | `grep -rnE 'schedule:\|cron:' <ci files>` near a `terraform plan` / `-detailed-exitcode` | ✅ |
