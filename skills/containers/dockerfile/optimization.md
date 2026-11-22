# Dockerfile optimization

**Contents:** Choosing a base image · Layer ordering · Cache mounts · Multi-stage builds · Build platform vs. target platform · Combining `RUN` instructions · Compiled languages · Secrets · Running as non-root · Signals and PID 1 · ENTRYPOINT and CMD · `HEALTHCHECK` · Logging · Labels and tags · When the build fails · Publishing: SBOM, provenance, signatures · Verification commands · Sources

The reference catalog behind [SKILL.md](SKILL.md). Each entry says what the technique buys and what it costs — a technique with no stated cost is usually one you don't understand yet.

---

## Choosing a base image

The base decides your size floor, your libc, your debuggability and most of your CVE surface. It is the highest-leverage line in the file and the one most often chosen by habit.

| Base | Size | Buys | Costs |
|---|---|---|---|
| `<lang>:<ver>` (full) | 300MB–1GB | Every build tool present; nothing to debug | Huge, wide CVE surface, slow pulls |
| `<lang>:<ver>-slim` | 50–200MB | Debian userland, glibc, a shell, a package manager | Still carries a full userland |
| `<lang>:<ver>-alpine` | 20–80MB | Smallest with a shell | **musl, not glibc** — native modules may need recompiling or fail subtly; DNS resolution differs; Python wheels often don't exist, so you compile |
| `gcr.io/distroless/<lang>` | 20–60MB | No shell, no package manager — a genuinely small attack surface | No shell means no `docker exec` debugging; needs a multi-stage build; awkward when the app shells out |
| `scratch` | 0 | Nothing but your binary | Only viable for a static binary (Go, Rust with musl target); no certs, no timezone data, no `/etc/passwd` unless you copy them |
| Hardened minimal (Chainguard, Docker Hardened Images, Ubuntu chiselled) | 10–60MB | Distroless-style surface with a vendor rebuilding it as CVEs land; usually non-root by default; SBOM and signature published | A vendor dependency, and often a paid one past the `latest` tag; same no-shell debugging cost as distroless |

**The default that is right most often: `-slim` for the runtime stage, the full image for the build stage.** You get glibc and a shell where you need them, and the toolchain never ships.

**A shell in the runtime image is a cost, not just a convenience.** It is what an attacker uses once they have code execution, and runtime monitors treat a shell starting in a production container as an incident. That is the real argument for distroless or a hardened minimal base — not the megabytes — and it's why the [debug stage](#a-debug-stage-instead-of-a-shell-in-production) below exists.

**Count, don't assert.** "Smaller attack surface" is a claim until a scanner gives it a number: `trivy image --severity HIGH,CRITICAL --ignore-unfixed <image>` on each candidate base, before and after. Scanners disagree with one another and report packages the app never loads, so use the count to compare options, not as a gate.

**Alpine's trap:** it looks like a pure size win and often isn't. On Python it forces source builds of wheels that have prebuilt manylinux binaries, which can turn a 40-second install into six minutes and produce a *larger* image once the compiler is in. Measure before adopting it.

### Pinning

```dockerfile
FROM node:20.11-slim@sha256:6b3cfc9a...
```

The tag says what you meant; the digest says what you got. Tags are mutable — `node:20.11-slim` is rebuilt when its Debian base is patched, so the same Dockerfile produces different images across weeks. That's usually good (you get the patches) and occasionally catastrophic (you get the regression), which is why anything shipping to production pins the digest and bumps it deliberately.

**"Deliberately" has to mean a bot.** A digest stops the regression *and* the patch. Pair it with Renovate or Dependabot (both update `FROM … @sha256:` lines and open a PR) or a scheduled rebuild; without one, the pin quietly turns into an unpatched image that gets older every week.

**Name the registry.** `docker.io/library/node:20.11-slim@sha256:…`, or your mirror's hostname. A short name resolves through whatever registry the builder is configured to try, which is a dependency-confusion surface in any setup with more than one.

**OS packages are the pin people forget.** `apt-get install libpq5` gets whatever the mirror holds on build day, so two builds of the same commit differ. The options, honestly: pin versions (`libpq5=15.6-0+deb12u1` — reproducible, and breaks when Debian drops the old version from its mirrors); move system packages into a base image built and tagged on its own schedule; or accept the drift and say so. The unpinned `apt-get` examples in this doc take the third option.

---

## Layer ordering — the cache rule

Docker caches per instruction and invalidates **every layer after** the first change. So the rule is: **order instructions by how often they change, rarest first.**

Dependencies change weekly. Source changes hourly. Therefore:

```dockerfile
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build
```

Never:

```dockerfile
COPY . .
RUN pnpm install   # every single commit reinstalls every dependency
```

This is the single most common Dockerfile defect and the easiest to verify — change a source file's content, rebuild, and look for `CACHED` on the install layer.

**What the cache actually keys on.** For `COPY` and `ADD`, a checksum of the copied files' *content* — modification times are ignored, which is why `touch` busts nothing and proves nothing. For `RUN`, only the **instruction text**: `RUN curl …/latest.tar.gz` or `RUN git clone …` is cached forever, whatever the remote now serves. Refresh deliberately: `docker build --pull` for a newer base, `--no-cache-filter <stage>` to redo one stage, and `ADD --checksum=sha256:… <url>` when a remote file must be fetched — it fails loudly if the content changes, rather than serving a stale or swapped copy.

**Copy the lockfile, not just the manifest.** `COPY package.json ./` alone means a lockfile-only change (a security bump) doesn't invalidate the install layer, and you build against stale dependencies.

**Use frozen installs.** `npm ci`, `pnpm install --frozen-lockfile`, `uv sync --frozen`, `bundle install --deployment`. These fail loudly when the lockfile and manifest disagree, instead of silently resolving something new — which is the behavior you want in a build that is supposed to be reproducible.

---

## Cache mounts

A package manager's own cache is useless inside a layer: it either bloats the image or is discarded. BuildKit's cache mounts keep it on the builder, across builds, out of the image:

```dockerfile
RUN --mount=type=cache,target=/root/.npm \
    npm ci
```

Targets by ecosystem: npm `/root/.npm` · pnpm `/pnpm/store` · yarn `/usr/local/share/.cache/yarn` · pip `/root/.cache/pip` · uv `/root/.cache/uv` · poetry `/root/.cache/pypoetry` · Go `/root/.cache/go-build` and `/go/pkg/mod` · Cargo `/usr/local/cargo/registry` · Maven `/root/.m2` · apt `/var/cache/apt` (with `rm -f /etc/apt/apt.conf.d/docker-clean` first).

**Cost:** the cache is builder-local. A cold CI runner gets no benefit unless the cache is exported, so this speeds up local iteration far more than it speeds up CI.

---

## Multi-stage builds

The purpose is not tidiness. It is that **the build stage's contents cannot reach the shipped image except by an explicit `COPY --from`.** A compiler, a header package, dev dependencies, the test suite and the source tree all stay behind by default rather than by discipline.

```dockerfile
FROM node:20.11-slim AS build
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/pnpm/store pnpm install --frozen-lockfile
COPY . .
RUN pnpm build && pnpm prune --prod

FROM node:20.11-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN groupadd -r -g 10001 app && useradd -r -u 10001 -g app app \
 && install -d -o app -g app /app/data
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
USER 10001:10001
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD node -e "fetch('http://localhost:3000/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "dist/server.js"]
```

**Name the stages.** `AS build` beats `--from=0`, which silently breaks when someone inserts a stage.

**The code is root's; only the data directory is the app's.** `COPY` without `--chown` lands root-owned whatever `USER` says, and that is what you want for code and dependencies: the app can read them and cannot rewrite them. Give the user only what Step 1 found it writes (`install -d -o app -g app /app/data` above). Where a copied path genuinely must be writable, use `COPY --chown=10001:10001` or `COPY --chmod`, **never a separate `RUN chown -R`** — a recursive chown on a copied `node_modules` duplicates the entire layer.

Extra stages are cheap and unbuilt stages cost nothing. A `test` stage that CI targets with `--target test` lets CI and production share exactly one dependency-install path.

**`ARG` is scoped per stage.** An `ARG` declared before the first `FROM` is visible only to `FROM` lines; a stage that uses it must redeclare `ARG NAME` (no value) inside. The symptom of forgetting is an empty variable and a build that silently does the wrong thing.

### A debug stage instead of a shell in production

Distroless's cost is that there is nothing to `exec` into. Rather than adding a shell to the production image, add a stage that is the runtime plus tools, and make sure it is **not the last stage** — `docker build` with no `--target` builds the last one:

```dockerfile
FROM runtime AS debug
USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl procps strace \
 && rm -rf /var/lib/apt/lists/*
USER 10001:10001

# the last stage is what a plain `docker build` produces: keep it the production image
FROM runtime AS default
```

`docker build --target debug -t app:debug .` when you need it. For a distroless runtime, base the debug stage on the vendor's `:debug` tag (which adds busybox) instead. On a cluster, an ephemeral debug container (`kubectl debug`) or a tools container sharing the target's namespaces (`docker run --pid container:<id> --network container:<id> nicolaka/netshoot`) does the same without rebuilding.

---

## Build platform vs. target platform

The build host and the deployment target are frequently different architectures — an Apple Silicon laptop (`linux/arm64` under Docker Desktop) building for an `linux/amd64` cluster is the ordinary case. Docker will do it without complaint by emulating through QEMU, and the result is a build several times slower than native plus an image that can behave differently from the one CI produced.

**Always state the target.** `docker build` defaults to the host's architecture, so the failure mode is silent until the image reaches the cluster and exits with `exec format error`.

### The two BuildKit variables

In a multi-stage Dockerfile, BuildKit supplies these automatically:

| Variable | Means |
|---|---|
| `BUILDPLATFORM` / `BUILDARCH` | the machine running the build |
| `TARGETPLATFORM` / `TARGETOS` / `TARGETARCH` | what the image is being built *for* |

### Pattern 1 — cross-compile (fast, when the toolchain allows)

For Go, Rust, .NET, and any build whose output is platform-independent (a JS bundle, a CSS build, a Python wheel-free install), pin the **build** stage to the native builder and only make the **runtime** stage foreign. The compiler runs at full native speed; nothing is emulated.

```dockerfile
FROM --platform=$BUILDPLATFORM golang:1.22 AS build
ARG TARGETOS TARGETARCH
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY . .
RUN --mount=type=cache,target=/root/.cache/go-build     CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH     go build -o /out/app ./cmd/app

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/app /app
USER nonroot:nonroot
ENTRYPOINT ["/app"]
```

`CGO_ENABLED=0` is what makes this work — with cgo on, Go needs a cross-compiling C toolchain and you are back to Pattern 2. Rust does the same thing with `--target x86_64-unknown-linux-musl`; .NET with `-r linux-x64`.

**Node and Python get a partial version of this.** A TypeScript emit or a webpack bundle is architecture-independent, so the build stage can run native. But `npm ci` resolves optional native dependencies against the *current* platform, so a `node_modules` installed on arm64 and copied into an amd64 runtime will break on anything with a prebuilt binary (`sharp`, `esbuild`, `better-sqlite3`, `bcrypt`). Install production dependencies in a stage that runs on the **target** platform, and keep only the platform-independent build output from the native stage.

### Pattern 2 — build on the target (correct, when cross-compiling isn't available)

When a dependency compiles against the runtime's ABI, the build stage has to run on the target platform. Omit `--platform` on the build stage and accept emulation:

```dockerfile
# no --platform: runs under emulation when cross-building
FROM python:3.12-slim AS build
RUN --mount=type=cache,target=/root/.cache/pip     pip install --prefix=/install -r requirements.txt
```

Emulated `pip install` of packages with C extensions is genuinely slow — minutes, not seconds. The mitigations, in order of effectiveness: use a **native remote builder** for that architecture (a cloud ARM or x86 runner) so nothing is emulated at all; make sure wheels are actually being used rather than source builds (`--only-binary=:all:` will fail loudly if a package would compile); and cache aggressively.

### Building and publishing

```bash
# One target, explicitly — the usual local case
docker build --platform linux/amd64 -t app .

# Both, published as one multi-platform manifest
docker buildx build --platform linux/amd64,linux/arm64 -t registry/app:1.2.3 --push .
```

On the classic image store, `buildx --push` is required for a multi-platform build: a manifest list carrying several architectures cannot exist there, so `--load` accepts only one platform. That surprises people who expect `docker images` to show the result. The **containerd image store** — the default on current Docker Desktop and on new Engine installs — can hold multi-platform images locally; `docker info -f '{{.DriverStatus}}'` shows which one you have (`io.containerd.snapshotter.v1` means containerd).

**Each platform is its own image.** It has its own layers, its own packages and its own vulnerabilities, so scan each one (`trivy image --platform linux/arm64 …`) rather than assuming the amd64 result covers both.

**Copying a multi-platform image between registries** with `docker pull` / `tag` / `push` copies only the host's platform and silently drops the rest. Use `docker buildx imagetools create -t <dest> <src>` or `crane copy`, which copy the whole manifest list.

**Check what you actually produced:**

```bash
docker image inspect app --format '{{.Os}}/{{.Architecture}}'   # a local single-platform image
docker buildx imagetools inspect registry/app:1.2.3             # a published manifest list
```

The first command is the one to run before every deploy from a laptop. It costs nothing and catches the entire class of "works on my machine, `exec format error` on the cluster."

---

## Combining `RUN` instructions

Each `RUN` is a layer, and **a file deleted in a later layer still occupies space in the earlier one**. So anything installed and removed must happen inside one instruction:

```dockerfile
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq-dev gcc \
 && rm -rf /var/lib/apt/lists/*
```

`--no-install-recommends` alone often halves an apt install. `rm -rf /var/lib/apt/lists/*` in a *separate* `RUN` saves nothing at all.

**The counter-pressure:** every combination is also a cache-invalidation unit. Merging an apt install with the app's dependency install means a system-package change reinstalls the app's dependencies too. Combine what must be atomic for size; keep separate what changes at different rates.

---

## Compiled languages — where the wins are largest

A compiled binary makes the runtime stage nearly empty, so these stacks get the biggest multi-stage payoff — from a ~1GB toolchain image to tens of megabytes.

### Go

```dockerfile
FROM --platform=$BUILDPLATFORM golang:1.22 AS build
ARG TARGETOS TARGETARCH
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod     --mount=type=cache,target=/root/.cache/go-build     CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH     go build -ldflags='-s -w' -o /out/app ./cmd/app

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/app /app
ENTRYPOINT ["/app"]
```

- **`CGO_ENABLED=0`** gives a static binary, which is what makes `distroless/static` or even `scratch` viable, and what makes cross-compiling free.
- **`-ldflags='-s -w'`** strips the symbol table and DWARF — typically 25–30% off the binary, at the cost of useless stack traces in a panic. Worth it for a service, not for something you debug in production.
- **Both cache mounts.** `go mod download` uses the module cache; `go build` uses the build cache. Mounting only the first leaves most of the rebuild time on the table.
- **On `scratch` you get nothing** — no CA certificates (so every HTTPS call fails), no timezone database, no `/etc/passwd`. `distroless/static` includes all three and is 2MB. Use it.

### Rust

```dockerfile
FROM rust:1.77 AS build
WORKDIR /src
COPY Cargo.toml Cargo.lock ./
# cache the dependency build with a stub main
RUN mkdir src && echo 'fn main(){}' > src/main.rs && cargo build --release && rm -rf src
COPY . .
RUN --mount=type=cache,target=/usr/local/cargo/registry     --mount=type=cache,target=/src/target     cargo build --release && cp target/release/app /out/app

FROM gcr.io/distroless/cc-debian12:nonroot
COPY --from=build /out/app /app
ENTRYPOINT ["/app"]
```

- **The dummy-`main.rs` trick** is the Rust equivalent of copying the manifest before the source: Cargo has no "install dependencies only" mode, so you build a stub to populate the dependency cache in its own layer. Ugly, and it saves minutes on every source-only rebuild. (`cargo-chef` automates it if the ugliness bothers you.)
- **`distroless/cc`, not `static`** — the default `gnu` target links glibc. For `distroless/static` or `scratch`, build against `x86_64-unknown-linux-musl`.
- **`target/` must be in `.dockerignore`.** It is routinely multiple gigabytes and is the single biggest build-context offender in any language.

### JVM (Java / Kotlin)

```dockerfile
FROM eclipse-temurin:21-jdk AS build
WORKDIR /src
COPY gradle/ gradle/
COPY gradlew build.gradle.kts settings.gradle.kts ./
RUN --mount=type=cache,target=/root/.gradle ./gradlew dependencies --no-daemon
COPY . .
RUN --mount=type=cache,target=/root/.gradle ./gradlew bootJar --no-daemon

# JRE, not JDK — roughly half the size
FROM eclipse-temurin:21-jre
WORKDIR /app
RUN useradd -r -u 10001 app
COPY --from=build /src/build/libs/*.jar app.jar
USER 10001:10001
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-jar", "app.jar"]
```

- **JRE in the runtime stage, JDK only in build.** The commonest JVM Dockerfile mistake, and it's a few hundred megabytes.
- **`-XX:MaxRAMPercentage`** — modern JVMs read the container's cgroup limit, but the default heap fraction is conservative. Without it, a container with a 2GB limit may cap the heap around 500MB and OOM while looking half-empty.
- **`--no-daemon`** — the Gradle daemon is pointless in a build container and occasionally hangs it.
- **`jlink` or a Spring Boot layered jar** cuts further if the size matters; both add real complexity, so reach for them when you've measured a reason to.

---

## Secrets

**Never:**

```dockerfile
ARG NPM_TOKEN            # visible in docker history
ENV API_KEY=sk-live-...  # visible to anyone who can inspect the image
COPY .env .              # in the layer forever
```

`docker history --no-trunc` prints build args and env. Deleting the file in a later instruction does not remove it from the earlier layer — the data is still in the image and still pullable.

**Instead — build-time secrets via a mount**, which is never written to a layer:

```dockerfile
RUN --mount=type=secret,id=npm_token \
    NPM_TOKEN=$(cat /run/secrets/npm_token) npm ci
```

```bash
docker build --secret id=npm_token,env=NPM_TOKEN .
```

Current Dockerfile frontends can expose the secret straight as an environment variable for that one `RUN`, or mount a whole config file where the tool expects it:

```dockerfile
RUN --mount=type=secret,id=npm_token,env=NPM_TOKEN npm ci
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
```

**A secret mount still leaks if the command writes it down.** `npm config set //registry…/:_authToken=$NPM_TOKEN` writes `~/.npmrc`, `git config credential…` writes `~/.gitconfig`, `pip config set` writes `pip.conf` — and that file is now in the layer, mount or not. Mount the config file itself (the second line above) so nothing is ever written. The same goes for build provenance: `--provenance=mode=max` records build arguments, so a secret passed as `ARG` lands in the attestation too.

**And runtime secrets come in at run time** — `docker run --env-file`, compose `env_file`, or the orchestrator's secret store. The image should be safe to push to a registry a stranger can read; if it isn't, the secret is in the wrong place.

---

## Running as non-root

```dockerfile
RUN groupadd -r -g 10001 app && useradd -r -u 10001 -g app -d /app app \
 && install -d -o app -g app /app/data /app/tmp
# no --chown: root-owned, so readable by the app and not rewritable
COPY --from=build /app/dist ./dist
USER 10001:10001
```

**What root in a container actually is.** By default it is uid 0 on the host kernel, held back by three things Docker applies on top of namespaces: a reduced capability set, the default seccomp profile, and an AppArmor or SELinux profile. An escape is root *plus* one of those failing — a kernel bug, an added capability, a sensitive mount, `--privileged`. Running as non-root takes away the first half of every such chain, which is why it's the default here. Under user-namespace remapping or rootless Docker, container root maps to an unprivileged host uid; that is a host setting, not something an image can rely on.

Gotchas, all of which show up as a container that builds and then crashes:

- **Write paths.** The app's log dir, cache dir, upload dir and any tmp path must be owned by the user. This is the usual cause of a permission error on first run. `WORKDIR` creates its directory owned by root.
- **Use a numeric `USER`.** Kubernetes' `runAsNonRoot: true` refuses to start an image whose `USER` is a name, because it cannot tell whether the name is root. `USER 10001:10001`, or `65532:65532` on distroless — which ships that uid as `nonroot`.
- **Pick a uid above the system range** (10000+). A low uid can coincide with a real user or a system account on the host, which shows up confusingly in host `ps` output and, on a shared bind mount, as real file access.
- **Ports below 1024.** Docker has let unprivileged processes bind them inside a container since Engine 20.10, but host networking and some Kubernetes runtimes don't. Bind 3000/8080 in the container and map it outside — for portability, not because Docker forces it.
- **`USER` goes after everything that needs root** — package installs, chowns — and before `CMD`.
- **`USER` is a default, not an enforcement.** `docker run -u 0` overrides it; only the runtime (Kubernetes `runAsNonRoot`, a policy engine) can enforce it.

### Setuid binaries undo `USER`

A setuid-root binary in the image — `su`, `passwd`, `mount`, older `ping` — runs as root whoever starts it, so a process that only needs to reach one gets uid 0 back. Strip the bits in the runtime stage, before `USER`:

```dockerfile
RUN find / -xdev -perm /6000 -type f -exec chmod a-s {} + || true
```

Check without needing a shell in the image: `docker export $(docker create <image>) | tar -tvf - | awk '$1 ~ /^-.*[sS]/'` should print nothing (the `^-` keeps it to regular files — Debian ships setgid *directories* like `/var/mail`, which are harmless). **Costs:** `su`, `sudo` and setuid `ping` stop working in the container — none of which belong in a production image. At run time, `--security-opt no-new-privileges` blocks the same escalation from outside the image; the two are independent controls and worth having both. Distroless images ship with none.

---

## Signals and PID 1

```dockerfile
CMD ["node", "dist/server.js"]        # exec form — your process is PID 1, gets SIGTERM
CMD node dist/server.js                # shell form — /bin/sh is PID 1 and swallows SIGTERM
```

Shell form means `docker stop` waits the full 10-second grace period and then `SIGKILL`s, so in-flight requests are dropped and nothing runs its shutdown handler. The symptom is "deploys drop connections," and the cause is a missing pair of brackets.

Your process is now PID 1, and PID 1 is special twice over:

- **The kernel gives it no default signal handlers.** A signal PID 1 hasn't installed a handler for is ignored, not fatal — so an app that never registers for `SIGTERM` (common in scripts and some runtimes) sits through the grace period even in exec form. The app must handle `SIGTERM`, or an init must stand in front of it.
- **It doesn't reap orphaned children.** If the app spawns subprocesses, zombies accumulate (visible in the PIDS column of `docker stats`).

For either, add an init: `docker run --init`, compose's `init: true`, or `tini` as the entrypoint. If neither applies, skip it — an init you don't need is another binary in the image.

**`STOPSIGNAL`** when the app drains on something other than `SIGTERM`: nginx finishes in-flight requests on `SIGQUIT`, and so does php-fpm. One line, and the graceful path is the one `docker stop` takes. If shutdown legitimately takes longer than ten seconds, raise the grace period where the container runs (`docker stop -t 30`, compose `stop_grace_period`, Kubernetes `terminationGracePeriodSeconds`) rather than letting it be killed mid-drain.

---

## ENTRYPOINT and CMD

They compose: the container runs `ENTRYPOINT` with `CMD` appended as its arguments, and anything after the image name in `docker run` **replaces `CMD`, not `ENTRYPOINT`**. That gives two honest shapes:

| Shape | Use when | Running something else |
|---|---|---|
| `CMD ["node", "dist/server.js"]` alone | The image also runs migrations, tests or admin commands | `docker run img node dist/migrate.js` — just works |
| `ENTRYPOINT ["/app"]` + `CMD ["--port", "8080"]` | The image is one binary and arguments are its whole interface | `docker run img --port 9090`; anything else needs `--entrypoint` |

**The trap is the second shape on an image that does more than one thing.** A compose `migrate` service with `command: ["node", "dist/migrate.js"]` against an image whose `ENTRYPOINT` starts the server does not run the migration — it starts the server with two extra arguments, and nothing fails loudly. Either keep the start command in `CMD`, or set `entrypoint:` explicitly on every one-off service.

**Shell-form `ENTRYPOINT` silently ignores `CMD` and every `docker run` argument**, on top of swallowing signals. There is no case for it.

### Entrypoint scripts

When start-up needs logic — reading a `*_FILE` secret into a variable, checking preconditions — a script is fine if it obeys three rules:

```sh
#!/bin/sh
set -eu
: "${DATABASE_URL:?DATABASE_URL must be set}"           # fail fast, by name, with a reason
[ -w /app/data ] || { echo "/app/data is not writable by uid $(id -u)" >&2; exit 1; }
exec "$@"                                               # hand PID 1 to the real process
```

- **`exec "$@"` last**, or the shell stays PID 1 and the signal dies in it.
- **Fail fast with a precise message** for missing config, unreadable secrets, unwritable volumes. A start-up check turns a mysterious crash twenty minutes in into a one-line error at boot.
- **`LF` line endings.** A script checked out with Windows `CRLF` fails as `exec … no such file or directory` on a file that plainly exists — exit 255 as an exec-form entrypoint, 127 when a shell runs it. Pin it with `*.sh text eol=lf` in `.gitattributes`.

A script needs a shell, which rules out distroless; that is the price.

---

## `HEALTHCHECK`

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:3000/health || exit 1
```

- **`--start-period`** is the one people omit. During it, failures don't count toward `--retries`, which is what stops a slow-booting app from being killed before it ever finishes starting.
- **The endpoint must be cheap and local.** A healthcheck that queries the database turns a slow query into a restart loop, and a restart loop into an outage. Check liveness here; check dependencies in a separate readiness endpoint the orchestrator polls.
- **Exit `1` for unhealthy, never anything else.** `0` is healthy, `1` unhealthy, and `2` is reserved — hence the `|| exit 1`, which also maps curl's own exit codes onto the one that counts.
- **Distroless has no shell and no curl** — use the language runtime (`CMD ["node", "-e", "..."]`) or omit and let the orchestrator own it.
- **Who reads it.** Compose reads it (`depends_on: service_healthy`); **Swarm** reads it per task, to replace unhealthy tasks and to decide whether a rolling update succeeded — keep it there; **Kubernetes ignores it** and runs the liveness and readiness probes in the manifest, so on Kubernetes it is dead configuration. Omit it there, with a comment saying the probes own health, because image scanners flag a missing `HEALTHCHECK` and the comment is the answer.
- **Plain Docker acts on nothing.** An `unhealthy` container under `restart: unless-stopped` stays up and unhealthy; only an orchestrator replaces it. The healthcheck is a signal, not a remedy.

---

## Logging

**Write to stdout and stderr, and nothing else.** That is what `docker logs`, `docker compose logs` and every log shipper read; a file inside the container is invisible to all of them and grows the writable layer until something runs out of disk.

- **An app that insists on a file:** symlink it — `RUN ln -sf /dev/stdout /var/log/app/access.log && ln -sf /dev/stderr /var/log/app/error.log` (this is how the official nginx image does it) — or change its config.
- **Rotation is the daemon's job now.** The default `json-file` driver never rotates; set `max-size`/`max-file` in `daemon.json`, or use the `local` driver, wherever the container runs. That's a host setting, not a Dockerfile line, but the handoff should say it.

---

## Labels and tags

```dockerfile
ARG VCS_REF
LABEL org.opencontainers.image.source="https://github.com/org/app" \
      org.opencontainers.image.revision="${VCS_REF}"
```

- **OCI keys** (`org.opencontainers.image.*`) are the ones registries and scanners read; Label Schema and `MAINTAINER` are dead.
- **Put a changing `ARG` (commit SHA, build date) in the last stage, at the end.** Its value changing invalidates every layer after it, so declared early it busts the whole cache on every build.
- **One image, every environment.** Build once, tag with something unique (`<sha>` or `<date>-<sha>`), and promote that same image through test, staging and production with configuration supplied at run time. An image per environment with config baked in means production runs an artifact nothing else ever tested. `latest` means "whatever was pushed last" and nothing more.

---

## When the build fails

BuildKit has no intermediate image IDs to `docker run` into, which is how older guides debug a broken `RUN`. The current moves:

- **See the whole output:** `docker build --progress=plain --no-cache-filter <stage> .` — the default progress view truncates exactly the error you need.
- **Stop just before the failure and look around:** split the failing `RUN` at the suspect command, put the stage boundary there, then `docker build --target <stage> -t dbg . && docker run --rm -it --entrypoint sh dbg`.
- **Reproduce, don't guess.** A build error often names a symptom (a missing header, a 404 from a mirror) several steps from its cause. Run the command by hand in that stage before changing anything.

---

## Publishing: SBOM, provenance, signatures

When the image leaves your machine for a registry, three cheap additions answer the questions people ask after the next CVE ("are we affected?", "was this built from that commit?"):

```bash
docker buildx build --platform linux/amd64 --sbom=true --provenance=mode=max \
  -t registry/app:1.2.3 --push .
docker buildx imagetools inspect registry/app:1.2.3 --format '{{json .SBOM}}'
cosign sign registry/app@sha256:<digest>          # sign by digest, never by tag
```

**Costs:** attestations need `--push` (or the containerd store), add entries to the manifest, and `mode=max` records build args — which is one more reason no secret is ever an `ARG`. Signing only helps if something verifies it at deploy time; that belongs to the platform, not this file. Docker Content Trust / Notary v1 is retired — don't start there.

---

## Verification commands

| Question | Command |
|---|---|
| Does it build? | `docker build -t app .` |
| How big? | `docker images app --format '{{.Size}}'` |
| Where did the size go? | `docker history app` |
| Any secret in an instruction? | `docker history --no-trunc app \| grep -iE 'token\|key\|secret\|password'` |
| Any secret in a layer's files? | `trivy image --scanners secret app` |
| Running as non-root? | `docker image inspect app --format '{{.Config.User}}'` and `docker run --rm --entrypoint "" app id` |
| Any setuid binary left? | `docker export $(docker create app) \| tar -tvf - \| awk '$1 ~ /^-.*[sS]/'` |
| Does the cache hold? | change a source file's content, rebuild, look for `CACHED` on the install layer (not `touch` — mtimes don't count) |
| Did it stay up? | `docker inspect -f '{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}}' <id>` |
| Is its healthcheck passing? | `docker inspect -f '{{json .State.Health}}' <id>` |
| What does it write? | exercise it, then `docker diff <id>` — every `A`/`C` line is a write path to own, mount or put on tmpfs |
| Does it survive hardening? | `docker run --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges app` |
| How many fixable CVEs? | `trivy image --severity HIGH,CRITICAL --ignore-unfixed app` |
| Lint the Dockerfile | `hadolint Dockerfile` |
| Right architecture? | `docker image inspect app --format '{{.Os}}/{{.Architecture}}'` |
| Right architectures, published? | `docker buildx imagetools inspect registry/app:tag` |
| Does it actually serve? | `docker run -d -p 3000:3000 app && curl localhost:3000/health` |
| Does it stop cleanly? | `time docker stop <id>` — near-instant means signals work; ~10s means shell form |

---

## Sources

- [Docker's own Dockerfile best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [BuildKit mount documentation](https://docs.docker.com/build/guide/mounts/) — cache and secret mounts
- [Distroless images](https://github.com/GoogleContainerTools/distroless)
- Liz Rice, *Container Security*, 2nd ed. (O'Reilly, 2025) — what root in a container is, setuid, secrets in layers, supply chain, SBOM and signing
- Jeff Nickoloff & Stephen Kuenzli, *Docker in Action*, 2nd ed. (Manning, 2019) — ENTRYPOINT/CMD, entrypoint scripts, `USER`, `VOLUME`, `ONBUILD`, labels, debug stages
- Sean Kane & Karl Matthias, *Docker: Up & Running*, 2nd ed. (O'Reilly, 2018) — the build cache, logging, one image per environment, debugging builds
- Nigel Poulton, *Docker Deep Dive* (2018) — cache checksums, image metadata, healthchecks under Swarm

The three older books predate BuildKit as the default builder and Compose v2; their build-debugging and legacy-builder advice was not carried over.
