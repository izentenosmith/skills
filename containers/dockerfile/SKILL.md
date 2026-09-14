---
name: dockerfile
description: Write or repair a production Dockerfile for this repo — stack detected from the source, multi-stage build, non-root runtime, pinned base — and generate or fix the .dockerignore that feeds it. Use when a repo needs containerizing, when an image is too large or rebuilds too slowly, or before wiring services together with docker-compose.
---

# 🐳 Dockerfile

## Where this fits

Two container skills, in order:

1. **dockerfile** (this skill) — one image per service, plus the `.dockerignore` that defines its build context
2. [docker-compose](../docker-compose/SKILL.md) — wires those images together with datastores, networks, volumes and health gates

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

- [ ] **Language and runtime version** — from the manifest and its version pin (`.nvmrc`, `engines`, `python_requires`, `go.mod`, `rust-toolchain`, `.ruby-version`, the framework's own lockfile). **Pin to what the repo already declares.** An image built on a different minor than CI is a class of bug that only shows in production.
- [ ] **Package manager and its lockfile** — this decides the dependency-install layer and whether a frozen install is possible (`npm ci`, `pnpm install --frozen-lockfile`, `uv sync --frozen`, `poetry install --no-root`, `bundle install --deployment`).
- [ ] **Does it build?** — a compile step, a bundler, a static asset pipeline, a TypeScript emit. This is what decides whether the image needs multiple stages.
- [ ] **The start command** — from the framework convention or the manifest's scripts, not from a guess.
- [ ] **Listening port**, and whether it is configurable by env var.
- [ ] **Native dependencies** — anything needing a compiler, headers, or a system library at build time (`node-gyp`, `psycopg2`, `pillow`, `nokogiri`, `cgo`). These are the reason a build stage needs packages the runtime stage must not carry.
- [ ] **Runtime-only assets** — migrations, templates, static files, locale data. What the app reads at runtime and would fail without.
- [ ] **The target platform**, and whether it matches the build machine. `linux/amd64` for most cloud runtimes, `linux/arm64` for Graviton, Ampere, and Apple Silicon. **An Apple Silicon laptop building for an amd64 cluster is the common case and the common failure** — Docker will emulate it silently, producing a build that takes several times longer and, where a native module or a compiled binary is involved, an image that behaves differently from the one CI produces. Ask or infer from the deploy config; don't assume the host.

State the result as a short inference block before writing anything:

> **Stack:** Node 20.11 (from `.nvmrc`) · pnpm (lockfile present) · TypeScript build to `dist/` · starts `node dist/server.js` on `PORT` (default 3000) · native: none · **target `linux/amd64`, building on `darwin/arm64` — cross-platform**

If a required fact genuinely isn't in the repo, say so and pick the conventional default explicitly — don't silently assume.

---

## 🧱 Step 2: Write the Dockerfile

**Multi-stage is the default**, and the split is not stylistic. It is what keeps the compiler, the dev dependencies and the source tree out of the shipped image. Skip multi-stage only for an interpreted app with no build step and no native deps — and say that's why.

The shape:

- [ ] **`FROM` a pinned base.** Tag *and* digest for anything that ships. `node:20.11-slim` is reproducible-ish; `node:20.11-slim@sha256:…` is reproducible. `latest` is not a version. See [optimization.md](optimization.md) for choosing between full / slim / alpine / distroless — that choice has real consequences (musl vs glibc, missing shell, debuggability) and is not just about megabytes.
- [ ] **Dependencies before source.** Copy the manifest and lockfile, install, *then* copy the source. This is the single highest-value line ordering in the file: source changes on every commit, dependencies change rarely, and getting this backwards means every build reinstalls everything. Use a frozen/`ci`-style install so the lockfile is authoritative.
- [ ] **A cache mount for the package cache** where the builder supports it — `--mount=type=cache,target=/root/.npm` and equivalents. Survives across builds without landing in a layer.
- [ ] **A runtime stage that copies only artifacts.** Built output, production dependencies, runtime assets. Not the source tree, not the toolchain, not the test suite.
- [ ] **A non-root user.** Create it, `chown` what needs writing, `USER` it before `CMD`. Root in a container is root on a namespace boundary, and every container escape starts by being root inside.
- [ ] **`ENV` for real configuration only** — never a secret, never a credential. Build args are visible in image history; `ENV` is visible to anything that runs `docker inspect`. Secrets come in at *run* time, or through `--mount=type=secret` at build time, and [optimization.md](optimization.md) covers both.
- [ ] **`EXPOSE` the port** — documentation for compose and for humans, not a security control.
- [ ] **A `HEALTHCHECK`** that hits a real readiness endpoint, or a deliberate omission because the orchestrator owns liveness. Say which. Compose's `depends_on: service_healthy` gate is only as good as this line.
- [ ] **`CMD` in exec form** (`CMD ["node", "dist/server.js"]`). Shell form wraps the process in `/bin/sh`, which swallows `SIGTERM` and turns every graceful shutdown into a 10-second kill.
- [ ] **Handle the platform explicitly when build and target differ.** Emulated builds are slow and quietly divergent. Where the toolchain can cross-compile (Go, Rust, .NET, and any build whose output is platform-independent), pin the build stage to the native builder with `FROM --platform=$BUILDPLATFORM` and target `$TARGETOS/$TARGETARCH` — the build runs at full speed and only the runtime stage is foreign. Where it cannot (a native module compiled against the runtime's ABI), the build stage must run on the target platform, and emulation is the price. [optimization.md](optimization.md) has both patterns and the `buildx` invocation for publishing a multi-platform image.

---

## 🚫 Step 3: Write the `.dockerignore`

**Write it before the first build, not after.** The build context is sent to the daemon in full before a single instruction runs, and a `COPY . .` over an unignored tree copies `.git`, `node_modules`, the local `.env` and every build artifact straight into a layer.

Three jobs, in descending order of what they cost you — see [dockerignore.md](dockerignore.md) for the full catalog and the reasoning behind each entry:

- [ ] **Secrets.** `.env`, `.env.*` (keeping `.env.example`), key material, certificates, cloud credential files. A secret copied into a layer stays in that layer forever — deleting it in a later instruction does not remove it, and anyone who pulls the image can read it.
- [ ] **Cache invalidation.** Local `node_modules`, `__pycache__`, `.venv`, `target/`, `dist/`, `.next/`, coverage output, test caches. These change on every local run, so leaving them in the context busts the `COPY` layer's cache constantly — *and* a host-built `node_modules` copied into a Linux image brings host-native binaries that will not run.
- [ ] **Context size.** `.git`, editor directories, docs, fixtures, screenshots, CI config, the IaC directory. Nothing here reaches the image, but all of it is transferred on every build.

Then **measure it**, don't assume it:

```bash
du -sh . && docker build -t <image> . 2>&1 | head -1
```

The build's first line reports the transferred context. Report it before and after — a repo that goes from 340MB to 2MB of context is the whole justification for the file, and it's a number, not a claim.

If an existing `.dockerignore` is present, treat it like the Dockerfile in **repair** mode: it is usually incomplete rather than wrong. Add what's missing; don't replace a curated file wholesale.

---

## ✅ Step 4: Verify

Nothing here is optional, and none of it is satisfied by reading the file:

- [ ] **It builds.** `docker build` exits 0.
- [ ] **It runs.** The container starts, stays up, and answers on its port. A container that builds and immediately exits is the most common false success in this work.
- [ ] **It rebuilds cheaply.** Touch one source file, rebuild, and confirm the dependency layer is `CACHED`. If it isn't, the layer order is wrong — this is the check that catches it.
- [ ] **It is the right architecture.** `docker image inspect <image> --format '{{.Os}}/{{.Architecture}}'` matches the target, not the build host. This is the check that catches an amd64 deployment silently receiving an arm64 image, which fails at `docker run` on the cluster and nowhere earlier.
- [ ] **It is not root.** `docker run --rm <image> id` reports a non-zero uid.
- [ ] **No secret in any layer.** `docker history --no-trunc <image>` shows no credential in an `ENV` or an `ARG`, and the context excluded the env files.
- [ ] **The size is accounted for.** `docker images <image>` — if it's much larger than the runtime stage should be, something from the build stage came along.

Report each as a fact with the command's output behind it. "Should work" is not a verification.

---

## 🛑 Stopping rule

Stop when all four hold:

- [ ] Every Step 4 check passes, each with its observed result stated.
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
2. **Pin everything.** Base image tag and digest, runtime version, dependencies via lockfile. An unpinned image is a build that produces a different artifact tomorrow.
3. **Build for the target, not for the laptop.** Where they differ, say so and handle it — an image that runs locally and not on the cluster has failed at the only thing it exists for.
4. **Never bake a secret.** Not in `ENV`, not in `ARG`, not in a file copied from the context. Layers are permanent and public.
5. **Verify by running, not by reading.** Every claim in Step 4 has a command behind it.
6. **In repair mode, name the defect before you fix it.** A rewrite is not a repair, and a Dockerfile that ships today has earned the benefit of the doubt.

## Handoff

Once the image builds, runs and rebuilds cheaply:

> `<image>` builds at `<size>` for `<platform>`, runs as non-root, and rebuilds with the dependency layer cached. Build context went from `<before>` to `<after>`. Run **[docker-compose](../docker-compose/SKILL.md)** next if this service needs a database, cache, queue or search engine alongside it — it wires this image to those with health gates and a `.env.example`.

State the size and context numbers out loud. They are the only evidence this stage did anything.
