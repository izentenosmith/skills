# Dockerfile optimization

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

**The default that is right most often: `-slim` for the runtime stage, the full image for the build stage.** You get glibc and a shell where you need them, and the toolchain never ships.

**Alpine's trap:** it looks like a pure size win and often isn't. On Python it forces source builds of wheels that have prebuilt manylinux binaries, which can turn a 40-second install into six minutes and produce a *larger* image once the compiler is in. Measure before adopting it.

### Pinning

```dockerfile
FROM node:20.11-slim@sha256:6b3cfc9a...
```

The tag says what you meant; the digest says what you got. Tags are mutable — `node:20.11-slim` is rebuilt when its Debian base is patched, so the same Dockerfile produces different images across weeks. That's usually good (you get the patches) and occasionally catastrophic (you get the regression), which is why anything shipping to production pins the digest and bumps it deliberately.

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

This is the single most common Dockerfile defect and the easiest to verify — touch a source file, rebuild, and look for `CACHED` on the install layer.

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
RUN groupadd -r app && useradd -r -g app app
COPY --from=build --chown=app:app /app/node_modules ./node_modules
COPY --from=build --chown=app:app /app/dist ./dist
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD node -e "fetch('http://localhost:3000/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "dist/server.js"]
```

**Name the stages.** `AS build` beats `--from=0`, which silently breaks when someone inserts a stage.

**`--chown` on the copy**, not a separate `RUN chown`. A recursive chown on a copied `node_modules` duplicates the entire layer.

Extra stages are cheap and unbuilt stages cost nothing. A `test` stage that CI targets with `--target test` lets CI and production share exactly one dependency-install path.

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
FROM python:3.12-slim AS build       # runs under emulation when cross-building
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

`buildx --push` is required for a multi-platform build: a manifest list carrying several architectures cannot exist in the local image store, so `--load` accepts only one platform. That surprises people who expect `docker images` to show the result.

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
RUN mkdir src && echo 'fn main(){}' > src/main.rs &&     cargo build --release && rm -rf src        # cache the dependency build
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

FROM eclipse-temurin:21-jre        # JRE, not JDK — roughly half the size
WORKDIR /app
RUN useradd -r -u 10001 app
COPY --from=build --chown=app:app /src/build/libs/*.jar app.jar
USER app
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

**And runtime secrets come in at run time** — `docker run --env-file`, compose `env_file`, or the orchestrator's secret store. The image should be safe to push to a registry a stranger can read; if it isn't, the secret is in the wrong place.

---

## Running as non-root

```dockerfile
RUN groupadd -r app && useradd -r -g app -d /app app
COPY --from=build --chown=app:app /app/dist ./dist
USER app
```

Root in a container is uid 0 on the host kernel, separated only by namespaces. Every container escape chain starts from being root inside.

Gotchas, all of which show up as a container that builds and then crashes:

- **Write paths.** The app's log dir, cache dir, upload dir and any tmp path must be owned by the user. This is the usual cause of a permission error on first run.
- **Ports below 1024** need root or `CAP_NET_BIND_SERVICE`. Bind 3000/8080 in the container and map it outside.
- **`USER` goes after everything that needs root** — package installs, chowns — and before `CMD`.
- **Distroless** ships `nonroot` (uid 65532); use `USER nonroot:nonroot` rather than creating one.

---

## Signals and PID 1

```dockerfile
CMD ["node", "dist/server.js"]        # exec form — your process is PID 1, gets SIGTERM
CMD node dist/server.js                # shell form — /bin/sh is PID 1 and swallows SIGTERM
```

Shell form means `docker stop` waits the full 10-second grace period and then `SIGKILL`s, so in-flight requests are dropped and nothing runs its shutdown handler. The symptom is "deploys drop connections," and the cause is a missing pair of brackets.

Your process is now PID 1, which does not reap orphaned children. If the app spawns subprocesses, add an init: `docker run --init`, compose's `init: true`, or `tini` as the entrypoint. If it doesn't, skip it — an init you don't need is another binary in the image.

An entrypoint script must `exec "$@"` as its last line, or the signal dies in the shell exactly as above.

---

## `HEALTHCHECK`

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:3000/health || exit 1
```

- **`--start-period`** is the one people omit. During it, failures don't count toward `--retries`, which is what stops a slow-booting app from being killed before it ever finishes starting.
- **The endpoint must be cheap and local.** A healthcheck that queries the database turns a slow query into a restart loop, and a restart loop into an outage. Check liveness here; check dependencies in a separate readiness endpoint the orchestrator polls.
- **Distroless has no shell and no curl** — use the language runtime (`CMD ["node", "-e", "..."]`) or omit and let the orchestrator own it.
- **On Kubernetes, omit it.** Liveness and readiness probes belong in the manifest, and two competing health systems is one too many. In compose it earns its place, because `depends_on: service_healthy` reads exactly this.

---

## Verification commands

| Question | Command |
|---|---|
| Does it build? | `docker build -t app .` |
| How big? | `docker images app --format '{{.Size}}'` |
| Where did the size go? | `docker history app` |
| Any secret baked in? | `docker history --no-trunc app \| grep -iE 'token\|key\|secret\|password'` |
| Running as non-root? | `docker run --rm app id` |
| Does the cache hold? | touch a source file, rebuild, look for `CACHED` on the install layer |
| Right architecture? | `docker image inspect app --format '{{.Os}}/{{.Architecture}}'` |
| Right architectures, published? | `docker buildx imagetools inspect registry/app:tag` |
| Does it actually serve? | `docker run -d -p 3000:3000 app && curl localhost:3000/health` |
| Does it stop cleanly? | `time docker stop <id>` — near-instant means signals work; ~10s means shell form |

---

## Sources

- [Docker's own Dockerfile best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [BuildKit mount documentation](https://docs.docker.com/build/guide/mounts/) — cache and secret mounts
- [Distroless images](https://github.com/GoogleContainerTools/distroless)
