# `.dockerignore`

**Contents:** Why this file is not optional · The baseline · Per-stack additions · Testing what you wrote · Patterns and their traps · Deny-all, then allow · One file per Dockerfile · Repairing an existing file

The reference catalog behind [SKILL.md](SKILL.md) Step 3.

---

## Why this file is not optional

Before Docker runs a single instruction, the **entire build context** — everything in the directory, recursively — is packaged and sent to the daemon. `.dockerignore` is the only thing that bounds it.

Three consequences, in the order they'll hurt you:

1. **Secrets become permanent.** `COPY . .` over an unignored tree copies your local `.env` into a layer. Layers are immutable: deleting the file in a later instruction leaves the data in the earlier one, readable by anyone who pulls the image. `docker history --no-trunc` finds it; so does anyone else.
2. **The cache stops working.** `node_modules`, `__pycache__`, `dist/` and coverage output change on every local run. If they're in the context, every `COPY . .` layer and everything after it is invalidated on every build — including the dependency install if the ordering is already wrong.
3. **Builds get slow.** A repo with a long history sends its whole `.git` directory — often the single largest thing in the context — over the wire on every build, to be used by nothing.

There's a fourth, subtler one: **a host-built `node_modules` or `.venv` copied into a Linux image carries host-native binaries.** On an Apple Silicon laptop building a linux/amd64 image, those are the wrong architecture. The failure is a runtime crash in a native module, which looks nothing like a Dockerfile problem.

---

## The baseline

Everything here applies to essentially any repo:

```gitignore
# Version control
.git
.gitignore
.gitattributes

# Docker's own files
Dockerfile*
.dockerignore
docker-compose*.yml
compose*.yaml

# Secrets — the important block. `**/` because a bare name only matches at the root.
**/.env
**/.env.*
!**/.env.example
**/*.pem
**/*.key
**/*.p12
**/*.pfx
**/secrets/
.aws/
.azure/
.gcloud/
.kube/
**/*kubeconfig*
.docker/
.ssh/
**/id_rsa*
**/id_ed25519*
.netrc
.pypirc
**/credentials.json
**/service-account*.json
**/*.tfvars

# Editors and OS
.vscode/
.idea/
*.swp
.DS_Store
Thumbs.db

# CI and tooling config that never reaches the image
.github/
.gitlab-ci.yml
.circleci/
.pre-commit-config.yaml

# Docs
*.md
!README.md
docs/
LICENSE

# Infrastructure
terraform/
*.tfstate*
k8s/
helm/
```

Two notes on the block that matters:

- **`.env.*` then `!.env.example`.** Order counts — the negation must come after the pattern it re-includes. Without it you exclude the template you wanted to ship.
- **`**/` on every secret pattern.** `.env` alone excludes the root `.env` and nothing else; a monorepo's `apps/api/.env` sails straight into `COPY . .`. See [the pattern table](#patterns-and-their-traps).
- **`.npmrc` is a judgement call.** A token-free one carrying settings the install needs (`node-linker`, a registry URL) has to stay in the context. One with an `_authToken` must not — exclude it and bring it back at build time as a secret mount (`--mount=type=secret,id=npmrc,target=/root/.npmrc`, in [optimization.md](optimization.md#secrets)). Same for `pip.conf` and `.pypirc` with credentials.
- **Exclude the `Dockerfile` itself.** It's read by the daemon from the context metadata, not copied — including it means editing a comment in it invalidates your `COPY . .` layer.

---

## Per-stack additions

**Node / TypeScript**
```gitignore
**/node_modules
npm-debug.log*
yarn-error.log
.pnpm-store/
dist/
build/
.next/
.nuxt/
.turbo/
coverage/
.eslintcache
*.tsbuildinfo
```
`**/node_modules` is the highest-value single line in any Node `.dockerignore` — usually hundreds of megabytes, always rebuilt in the image, and actively harmful if copied across architectures. The `**/` catches each workspace's copy in a monorepo; bare `node_modules` stops at the root.

Exclude `dist/` and build it in the image. A host-built `dist/` in the context means you ship whatever was last built locally, which is not necessarily what's in the source.

**Python**
```gitignore
**/__pycache__/
**/*.py[cod]
.venv/
venv/
env/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.tox/
.coverage
htmlcov/
```

**Go**
```gitignore
# vendor/ only if the build doesn't use it — see below
vendor/
bin/
*.test
```
Keep `vendor/` if the build uses `-mod=vendor`.

**Rust**
```gitignore
target/
```
`target/` is routinely multiple gigabytes and is the whole story on a slow Rust build context.

**Java / JVM**
```gitignore
target/
build/
.gradle/
*.class
```

**Ruby**
```gitignore
.bundle/
vendor/bundle/
log/
tmp/
```

**PHP**
```gitignore
vendor/
var/cache/
var/log/
```

---

## Testing what you wrote

**Measure the context.** BuildKit reports it on the `transferring context:` line:

```bash
docker build --progress=plain -t app . 2>&1 | grep 'transferring context'
# #4 transferring context: 1.82MB 0.1s done
```

Compare against `du -sh .`. A repo where those two numbers are close has an ineffective `.dockerignore`.

**See what actually landed:**

```bash
docker run --rm --entrypoint find app /app -maxdepth 2
```

(`--entrypoint`, because with an `ENTRYPOINT` in the image a bare `docker run app find …` hands `find` to the app as an argument. A distroless image has no `find`: `docker export $(docker create app) | tar -t | grep '^app/' | head -50` does the same from outside.)

Anything surprising in there came from the context.

**Check the layers for secrets:**

```bash
docker history --no-trunc app | grep -iE 'token|key|secret|password'   # instruction text only
trivy image --scanners secret app                                       # the files in every layer
```

The first catches a secret in an `ENV`, `ARG` or `RUN` line; only the second catches a key file that came in through `COPY . .`, which is the leak this file exists to prevent.

---

## Patterns and their traps

`.dockerignore` uses Go's `filepath.Match`, **not** gitignore syntax. The differences bite:

| Pattern | Matches |
|---|---|
| `node_modules` | only at the context root |
| `/node_modules` | the same — a leading `/` changes nothing, the root is implied |
| `**/node_modules` | that name at **any** depth |
| `*.log` | `.log` files at the root **only** |
| `**/*.log` | `.log` files at any depth |
| `!.env.example` | re-includes, and **must follow** the pattern that excluded it |

**The trap:** `*.log` does not recurse the way it does in `.gitignore`. Use `**/*.log` when you mean everywhere.

**Every pattern is anchored at the context root** — this is the biggest difference from `.gitignore`, where a bare name matches at any depth. `node_modules` excludes the root copy and lets every nested workspace's copy through; `.env` excludes the root env file and ships `apps/api/.env`. In a monorepo, or anywhere a name can recur, write `**/`.

**Comments must be whole lines.** `vendor/   # only if…` is not a pattern with a comment — it's a pattern that matches nothing.

---

## Deny-all, then allow

For a service in a large monorepo, listing exclusions is a losing game. Invert it:

```gitignore
*
!package.json
!pnpm-lock.yaml
!src/
!tsconfig.json
```

**Buys:** a new top-level directory can't silently enter the context, and the context is provably minimal.
**Costs:** a new legitimate input is silently *missing* instead, and the failure ("module not found" at build time) is less obvious than a bloated context. Use it where the context is otherwise unmanageable; the explicit list is friendlier everywhere else.

---

## One file per Dockerfile

A monorepo with several services can give each its own ignore file:

```bash
docker build -f services/api/Dockerfile -t api .
# reads services/api/Dockerfile.dockerignore if present, else ./.dockerignore
```

Useful when the API build needs `packages/shared/` and the worker build doesn't — each context stays minimal rather than being the union of everyone's needs.

---

## Repairing an existing file

Treat an existing `.dockerignore` as **incomplete rather than wrong**. Someone added entries for reasons that may not be visible, and a wholesale replacement drops them.

The productive pass:

1. Measure the current context (`docker build` first line vs `du -sh .`).
2. Find the biggest things still coming through: `du -sh .[!.]* * | sort -rh | head -20`.
3. Check the secret block specifically — it's the most commonly missing part and the only one with a permanent consequence.
4. Add what's missing; leave what's there.
