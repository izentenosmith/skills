---
name: dockerfile
description: Write or repair a production Dockerfile for this repo — stack detected from the source, multi-stage build, non-root runtime, pinned base — and generate or fix the .dockerignore that feeds it. Use when a repo needs containerizing, when an image is too large or rebuilds too slowly, or before wiring services together with docker-compose.
---

# 🐳 Dockerfile

## Where this fits

The container skills:

1. **dockerfile** (this skill) — one image per service, plus the `.dockerignore` that defines its build context
2. [docker-compose](../docker-compose/SKILL.md) — wires those images together with datastores, networks, volumes and health gates
3. [container-hardening](../container-hardening/SKILL.md) — reviews how containers run wherever they run; its image findings (no `USER`, setuid binaries, a secret in a layer, an unpinned base) come back here to be fixed
4. [container-debug](../container-debug/SKILL.md) — when a container won't start, stay up or connect: reads the runtime's own record, matches the symptom, proves the cause, and routes the fix back to the skill that owns it
5. [docker-swarm](../docker-swarm/SKILL.md) — reviews or designs a Swarm cluster and the stack files `docker stack deploy` runs

Run this first. Compose orchestrates images; it cannot fix a bad one. A service whose image is already correct gets composed in minutes, and a service whose image is wrong fails in a way that looks like an orchestration bug.

The `.dockerignore` is **part of this skill, not an afterthought**. It defines the build context, and the build context determines what gets sent to the daemon, what invalidates the cache, and what secrets end up in a layer. A perfect Dockerfile over an unbounded context is still slow and still leaky.

It leans on two reference docs:

- [optimization.md](optimization.md) — layer order, cache mounts, base image choice, the size/security trade-offs
- [dockerignore.md](dockerignore.md) — what to exclude and what each exclusion actually buys

---

## 📐 Calibrate the pass

Match the work to what's in front of you, and say which you picked:

- **Greenfield** — no Dockerfile exists. Work Steps 1–4 in order; you are choosing the whole shape.
- **Repair** — a Dockerfile exists and something is wrong (too large, rebuilds from scratch, runs as root, leaks a secret). **Read the existing file first and name the specific defect before changing a line.** Rewriting a working Dockerfile because you'd have written it differently is the most expensive way to introduce a regression into something that was shipping.
- **Audit only** — the user wants to know what's wrong, not a new file. Work Step 1 and the Step 4 checklist, report findings with severity, change nothing.

---

## 🔍 Step 1: Read the stack off the repo

Do not ask what the stack is. Infer it, then state the inference so it can be corrected:

- [ ] **Language and runtime version** — from the manifest and its version pin (`.nvmrc`, `engines`, `python_requires`, `go.mod`, `rust-toolchain`, `.ruby-version`, the framework's own lockfile). **Pin to what the repo already declares.** An image built on a different minor than CI is a class of bug that only shows in production. Then check that the line is **still supported** — a carefully pinned base on an end-of-life runtime or distro gets no more patches, and its `apt-get update` eventually stops working. If it's past end of life, say so; the upgrade is the user's call, not a side effect of this pass.
- [ ] **Package manager and its lockfile** — this decides the dependency-install layer and whether a frozen install is possible (`npm ci`, `pnpm install --frozen-lockfile`, `uv sync --frozen`, `poetry install --no-root`, `bundle install --deployment`).
- [ ] **Does it build?** — a compile step, a bundler, a static asset pipeline, a TypeScript emit. This is what decides whether the image needs multiple stages.
- [ ] **The start command** — from the framework convention or the manifest's scripts, not from a guess.
- [ ] **Listening port**, and whether it is configurable by env var.
- [ ] **Native dependencies** — anything needing a compiler, headers, or a system library at build time (`node-gyp`, `psycopg2`, `pillow`, `nokogiri`, `cgo`). These are the reason a build stage needs packages the runtime stage must not carry.
- [ ] **Runtime-only assets** — migrations, templates, static files, locale data. What the app reads at runtime and would fail without.
- [ ] **What it writes at runtime** — upload and cache directories, a SQLite file, a pid file, anything under `/tmp`. This list decides which paths the non-root user must own, and which need a volume or `tmpfs` once the root filesystem is made read-only. The usual first-run crash after dropping root is a write path nobody listed.
- [ ] **Where it logs.** A container's logs are its stdout and stderr; an app that writes to a file inside the container hides its output from `docker logs` and grows the writable layer until the disk fills. Note the config change or symlink (`ln -sf /dev/stdout /var/log/app.log`) that redirects it.
- [ ] **Does anything run other than the server?** Migrations, a test suite, a one-off admin command run in the same image. That decides whether the start command goes in `ENTRYPOINT` or `CMD` — see [optimization.md](optimization.md#entrypoint-and-cmd).
- [ ] **The target platform**, and whether it matches the build machine. `linux/amd64` for most cloud runtimes, `linux/arm64` for Graviton, Ampere, and Apple Silicon. **An Apple Silicon laptop building for an amd64 cluster is the common case and the common failure** — Docker will emulate it silently, producing a build that takes several times longer and, where a native module or a compiled binary is involved, an image that behaves differently from the one CI produces. Ask or infer from the deploy config; don't assume the host.

State the result as a short inference block before writing anything:

> **Stack:** Node 20.11 (from `.nvmrc`) · pnpm (lockfile present) · TypeScript build to `dist/` · starts `node dist/server.js` on `PORT` (default 3000) · native: none · **target `linux/amd64`, building on `darwin/arm64` — cross-platform**

If a required fact genuinely isn't in the repo, say so and pick the conventional default explicitly — don't silently assume.

---

## 🧱 Step 2: Write the Dockerfile

**Multi-stage is the default**, and the split is not stylistic. It is what keeps the compiler, the dev dependencies and the source tree out of the shipped image. Skip multi-stage only for an interpreted app with no build step and no native deps — and say that's why.

The shape:

- [ ] **`FROM` a pinned base.** Tag *and* digest for anything that ships. `node:20.11-slim` is reproducible-ish; `node:20.11-slim@sha256:…` is reproducible. `latest` is not a version. **A digest is only safe with something that bumps it** — Renovate, Dependabot, a scheduled rebuild — because a digest nobody updates freezes today's CVEs in place for good. If the repo has no such bot, say so in the handoff. See [optimization.md](optimization.md) for choosing between full / slim / alpine / distroless / hardened minimal images — that choice has real consequences (musl vs glibc, missing shell, debuggability) and is not just about megabytes.
- [ ] **Dependencies before source.** Copy the manifest and lockfile, install, *then* copy the source. This is the single highest-value line ordering in the file: source changes on every commit, dependencies change rarely, and getting this backwards means every build reinstalls everything. Use a frozen/`ci`-style install so the lockfile is authoritative.
- [ ] **A cache mount for the package cache** where the builder supports it — `--mount=type=cache,target=/root/.npm` and equivalents. Survives across builds without landing in a layer.
- [ ] **A runtime stage that copies only artifacts.** Built output, production dependencies, runtime assets. Not the source tree, not the toolchain, not the test suite.
- [ ] **A non-root user, switched to by number.** Create it, give it the Step 1 write paths, and `USER 10001:10001` before `CMD`. **Numeric, not a name**: Kubernetes' `runAsNonRoot` cannot verify that a name isn't root and refuses to start the pod. **The app's code stays owned by root** and is only readable by the user — a process that owns its own code can rewrite it once compromised — so `chown` the write paths, not the whole tree. (`WORKDIR` creates its directory owned by root; a non-root app that writes to its working directory needs that path chowned.) Root inside a container is held back by dropped capabilities, seccomp and AppArmor/SELinux, but those are the layers an escape goes through, and without user-namespace remapping container root *is* host uid 0 the moment it gets out.
- [ ] **`ENV` for real configuration only** — never a secret, never a credential. Build args are visible in image history; `ENV` is visible to anything that runs `docker inspect`. Secrets come in at *run* time, or through `--mount=type=secret` at build time, and [optimization.md](optimization.md) covers both.
- [ ] **`EXPOSE` the port** — documentation for compose and for humans, not a security control.
- [ ] **A `HEALTHCHECK`** that hits a real endpoint, or a deliberate omission because the orchestrator owns health. Say which, in a comment in the file — image scanners flag a missing `HEALTHCHECK`, and the comment is the answer to that finding. Compose's `depends_on: service_healthy` gate and Swarm's rolling updates both read this line; Kubernetes ignores it.
- [ ] **`CMD` in exec form** (`CMD ["node", "dist/server.js"]`). Shell form wraps the process in `/bin/sh`, which swallows `SIGTERM` and turns every graceful shutdown into a 10-second kill. A **shell-form `ENTRYPOINT`** is worse: it also silently discards `CMD` and every argument passed to `docker run`. If the image must also run migrations or tests, keep the start command overridable — [optimization.md](optimization.md#entrypoint-and-cmd) has the contract.
- [ ] **Nothing in the image that changes what a container does later.** No `VOLUME` (it creates a stray anonymous volume on every run and can't be read-only; declare volumes in compose or the manifest), no `ONBUILD` (triggers that fire invisibly in someone else's build), `COPY` rather than `ADD` (which silently unpacks archives and fetches URLs), and no package installs in the entrypoint (code installed at start is unscanned, absent from the SBOM, and impossible on a read-only root filesystem).
- [ ] **Handle the platform explicitly when build and target differ.** Emulated builds are slow and quietly divergent. Where the toolchain can cross-compile (Go, Rust, .NET, and any build whose output is platform-independent), pin the build stage to the native builder with `FROM --platform=$BUILDPLATFORM` and target `$TARGETOS/$TARGETARCH` — the build runs at full speed and only the runtime stage is foreign. Where it cannot (a native module compiled against the runtime's ABI), the build stage must run on the target platform, and emulation is the price. [optimization.md](optimization.md) has both patterns and the `buildx` invocation for publishing a multi-platform image.

---

## 🚫 Step 3: Write the `.dockerignore`

**Write it before the first build, not after.** The build context is sent to the daemon in full before a single instruction runs, and a `COPY . .` over an unignored tree copies `.git`, `node_modules`, the local `.env` and every build artifact straight into a layer.

Three jobs, in descending order of what they cost you — see [dockerignore.md](dockerignore.md) for the full catalog and the reasoning behind each entry:

- [ ] **Secrets.** `.env`, `.env.*` (keeping `.env.example`), key material, certificates, cloud and registry credential files, a tokened `.npmrc`. **Write them as `**/.env`** — `.dockerignore` patterns are anchored at the context root, unlike `.gitignore`, so a bare `.env` lets every nested `apps/*/.env` through. A secret copied into a layer stays in that layer forever — deleting it in a later instruction does not remove it, and anyone who pulls the image can read it.
- [ ] **Cache invalidation.** Local `node_modules`, `__pycache__`, `.venv`, `target/`, `dist/`, `.next/`, coverage output, test caches. These change on every local run, so leaving them in the context busts the `COPY` layer's cache constantly — *and* a host-built `node_modules` copied into a Linux image brings host-native binaries that will not run.
- [ ] **Context size.** `.git`, editor directories, docs, fixtures, screenshots, CI config, the IaC directory. Nothing here reaches the image, but all of it is transferred on every build.

Then **measure it**, don't assume it:

```bash
du -sh . && docker build --progress=plain -t <image> . 2>&1 | grep 'transferring context'
```

BuildKit reports the transferred context on its `transferring context:` line; with plain progress it's greppable. Report it before and after — a repo that goes from 340MB to 2MB of context is the whole justification for the file, and it's a number, not a claim.

If an existing `.dockerignore` is present, treat it like the Dockerfile in **repair** mode: it is usually incomplete rather than wrong. Add what's missing; don't replace a curated file wholesale.

---

## ✅ Step 4: Verify

Nothing here is optional, and none of it is satisfied by reading the file:

- [ ] **It builds.** `docker build -t <image> .` exits 0.
- [ ] **It runs, and stays running.** `docker run -d -p <port>:<port> --name <image>-check <image>`, then `curl -fsS localhost:<port>/<health path>`: the container starts, stays up, and answers on its port. `docker run -d` exits 0 even when the container dies a second later, so after a few seconds also read `docker inspect -f '{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}} {{.RestartCount}}' <image>-check` (expect `running 0 false 0`), and, with a `HEALTHCHECK`, wait for `docker inspect -f '{{.State.Health.Status}}'` to read `healthy` — a curl from the host never exercises the image's own healthcheck line. A container that builds and immediately exits is the most common false success in this work. If the app needs env vars or a database just to boot, run it with a stub `.env` and say so.
- [ ] **It rebuilds cheaply.** **Change a source file's content** — append a comment to one file — rebuild with `docker build --progress=plain -t <image> .`, confirm the dependency layer is `CACHED` and the `COPY` of the source is not, then restore the file (`git checkout -- <file>`). **`touch` proves nothing**: the build cache keys `COPY` on file content, not modification time, so a touched file leaves *every* layer cached and a Dockerfile with the wrong order passes too. If the dependency layer re-runs, the layer order is wrong — this is the check that catches it.
- [ ] **It is the right architecture.** `docker image inspect <image> --format '{{.Os}}/{{.Architecture}}'` matches the target, not the build host. This is the check that catches an amd64 deployment silently receiving an arm64 image, which fails at `docker run` on the cluster and nowhere earlier.
- [ ] **It is not root.** `docker image inspect <image> --format '{{.Config.User}}'` is a non-zero numeric uid (empty means root), and `docker run --rm --entrypoint "" <image> id` reports it. **The `--entrypoint ""` matters**: with an `ENTRYPOINT`, a bare `docker run <image> id` passes `id` to the app as an argument. A distroless image has no `id` binary; the metadata check stands alone there. An entrypoint that switches user itself (gosu, su-exec) makes the metadata lie — check `docker top <image>-check` on the running container instead.
- [ ] **No secret in any layer.** `docker history --no-trunc <image>` shows no credential in an `ENV`, an `ARG` or a `RUN` line, and the context excluded the env files. **`docker history` only shows instruction text** — a key file copied in and deleted later, or written by a `RUN`, is still in its layer and never appears there. Where a scanner is available, `trivy image --scanners secret <image>` reads layer *contents*. Search for a secret by its **name** (`grep -iE 'API_KEY|SECRET|TOKEN'`), never by printing its value. A command that would print one (`env`, `cat .env`, `docker inspect` on an old image) has its output cut to names (`cut -d= -f1`) before you quote it.
- [ ] **It stops cleanly.** `time docker stop <image>-check` returns in about a second. Ten seconds means `SIGTERM` never reached the app — shell form, an entrypoint script without `exec`, or a PID 1 with no `SIGTERM` handler — see [optimization.md](optimization.md#signals-and-pid-1).
- [ ] **The size is accounted for.** `docker images <image>` — if it's much larger than the runtime stage should be, something from the build stage came along. `docker history <image>` says which layer.
- [ ] **The context is measured.** `du -sh .` and BuildKit's `transferring context:` line from Step 3, before and after the `.dockerignore` change, as a row of the table like every other check.

Two more are worth running when the tools exist, and are reported the same way. Neither gates the stopping rule:

- [ ] **It survives runtime hardening.** `docker run -d --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges -p <port>:<port> <image>`, then curl it again. This is what a hardened orchestrator (Kubernetes' `restricted` policy, a [container-hardening](../container-hardening/SKILL.md) review) will impose; a failure here is a write path or a capability the app needs, found now instead of at deploy. Record each one it needs.
- [ ] **Its vulnerabilities are counted.** `trivy image --severity HIGH,CRITICAL --ignore-unfixed <image>`, before and after. This is the number behind "smaller attack surface" — report it, don't gate on it; scanners disagree with each other and carry false positives.

Report every check as a row of one table, **the command beside the result**, so anyone can re-run it:

```markdown
| Check | Command | Observed |
|---|---|---|
| Not root | `docker run --rm --entrypoint "" app:after id` | `uid=10001(app) gid=10001(app)` |
| Architecture | `docker image inspect app:after --format '{{.Os}}/{{.Architecture}}'` | `linux/amd64` |
```

"Should work" is not a verification, and neither is a result with no command behind it.

**No Docker where you are working?** Then nothing here was verified, and the report says so in its first line: *"Docker is not available here, so none of these checks were run."* Still write the files, still fill the table with every command, and mark each Observed cell `not run`. Hand the table to the user as the checks to run. Never infer an outcome from reading the file and present it as observed.

---

## 🛑 Stopping rule

Stop when all four hold:

- [ ] Every Step 4 check passes, each with its command and its observed result stated (or, with no Docker, each command listed as `not run`).
- [ ] The image carries **nothing it doesn't need at runtime** — no compiler, no dev dependencies, no source tree in a compiled stack.
- [ ] The `.dockerignore` covers the three categories above, with the measured context size reported.
- [ ] Any remaining defect is **recorded with its reason for staying** — a base image you can't slim without losing a system library, a root requirement from a runtime you don't control.

Then stop. There is always another 8MB. **An optimization that doesn't reduce build time, image size, or attack surface by an amount someone would notice is a diff for its own sake** — it costs review attention and it risks breaking a build that works. Chasing the last megabyte of a 200MB image is the way this skill turns into a hobby.

---

## Subagents — optional

Rarely worth it. A Dockerfile is one small file and the whole job fits in view.

The exception is a **monorepo with several deployable services**. There, Step 1 delegates: one subagent per service to infer its stack, read-only, returning the inference block above. Steps 2–4 stay in the main thread — the images usually share a base and a layer strategy, and that is exactly the commonality a parallel fan-out destroys.

**Dispatch contract.** A subagent starts with no history. Give each one the **prior**, the **target** (which service directory it owns, and that the others are covered so it neither duplicates nor apologises for the gap), the **context it cannot infer** (the deployment target, the registry, any base-image standard the org already has), the **return shape** — the Step 1 inference block, including "could not determine" per field so a silent delegate is distinguishable from a clean read — and an explicit *"report conclusions, not file excerpts."* Delegates stay **read-only**: two agents writing one tree clobber each other.

---

## Rules of Engagement

1. **Infer the stack, don't ask for it.** The repo already says what it is. Ask only when the repo genuinely contradicts itself.
2. **Pin everything, and keep the pins moving.** Base image tag and digest, runtime version, dependencies via lockfile. An unpinned image is a build that produces a different artifact tomorrow; a pinned one nobody bumps is a build that ships last year's CVEs.
3. **Build for the target, not for the laptop.** Where they differ, say so and handle it — an image that runs locally and not on the cluster has failed at the only thing it exists for.
4. **Never bake a secret, and never repeat one.** Not in `ENV`, not in `ARG`, not in a file copied from the context. Layers are permanent and public. When you find one already baked in, name the variable and where it was (`Dockerfile:12`, the copied `.env`), never its value: not in your response, the fixed files, a check's quoted output or a comment. Then tell the user to **rotate it**, because every image built so far still carries it.
5. **Verify by running, not by reading.** Every claim in Step 4 has a command behind it.
6. **In repair mode, name the defect before you fix it.** A rewrite is not a repair, and a Dockerfile that ships today has earned the benefit of the doubt.

## Handoff

Once the image builds, runs and rebuilds cheaply:

> `<image>` builds at `<size>` for `<platform>`, runs as non-root, and rebuilds with the dependency layer cached. Build context went from `<before>` to `<after>`. Base pinned at `<digest>`, bumped by `<bot, or "nothing yet">`. Run **[docker-compose](../docker-compose/SKILL.md)** next if this service needs a database, cache, queue or search engine alongside it — it wires this image to those with health gates and a `.env.example`.

State the size and context numbers out loud. They are the only evidence this stage did anything.
