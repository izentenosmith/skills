# Environments, overrides and secrets

The reference behind [SKILL.md](SKILL.md) Step 5.

---

## The three files

| File | Committed? | Holds |
|---|---|---|
| `docker-compose.yml` | yes | The stack as it would run anywhere — services, images, networks, volumes, health gates |
| `docker-compose.override.yml` | yes | The dev-only parts — source mounts, hot reload, debug ports, published database ports |
| `.env` | **no** | Actual values for this machine |
| `.env.example` | yes | Every variable the stack reads, documented, with safe local values |

`docker compose up` **automatically merges the base and the override**. That's the whole design: the default command gives a developer the dev experience, and `docker compose -f docker-compose.yml up` gives the clean stack for CI or a smoke test.

The rule that keeps it working: **the base file must stay deployable on its own.** The moment a source bind mount or a `--reload` flag lands in the base, there is no clean variant left and the split has bought you nothing.

---

## What goes where

**Base:**

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      NODE_ENV: ${NODE_ENV:-production}
      DATABASE_URL: ${DATABASE_URL}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
```

**Override:**

```yaml
services:
  api:
    build:
      target: development      # stop at the build stage, keep dev dependencies
    command: ["npm", "run", "dev"]
    environment:
      NODE_ENV: development
      LOG_LEVEL: debug
    volumes:
      - ./src:/app/src:cached
      - /app/node_modules      # anonymous volume — see below
    ports:
      - "9229:9229"            # debugger
  postgres:
    ports:
      - "5432:5432"            # so a local GUI can connect
```

**The anonymous `- /app/node_modules` line is not a typo.** Bind-mounting `./src` (or worse, `.`) shadows what the image built at that path. An anonymous volume on `node_modules` masks the bind mount there and preserves the container's own copy — which matters because the host's `node_modules` was built for the host's architecture and often won't run. Same pattern for `.venv`, `target/`, `vendor/`.

---

## Merge rules that surprise people

Compose merges base and override per key, and the rule is not uniform:

- **Scalars replace.** `image`, `command`, `user` — the override wins outright.
- **Mappings merge per key.** `environment`, `labels` — the override adds and replaces individual keys, keeping the rest.
- **Sequences append.** `ports`, `volumes`, `dns` — the override's entries are **added**, not substituted.

That last one is the trap: you cannot *remove* a published port in an override, only add more. A base that publishes `5432:5432` cannot be un-published by any override, so it will collide with every other project using Postgres on that machine. **Publish in the override; never in the base.**

`depends_on` merges by service name, so an override can tighten a condition but not drop the dependency.

---

## `develop.watch` — the better bind mount

Compose's file-sync feature does what a source bind mount was always being used for, without the bind mount's problems:

```yaml
services:
  api:
    build: .
    develop:
      watch:
        - action: sync            # copy changed files into the container
          path: ./src
          target: /app/src
          ignore: [node_modules/]
        - action: rebuild         # dependencies changed — rebuild the image
          path: ./package.json
        - action: sync+restart    # config changed — sync, then restart the process
          path: ./config
          target: /app/config
```

Run it with `docker compose watch` (or `docker compose up --watch`).

**Why it beats a bind mount**, which is the pattern most compose files still use:

- **It syncs instead of shadowing.** A bind mount replaces the container's directory wholesale, which is why every Node setup needs the anonymous-volume trick above to protect `node_modules`. `sync` copies individual files into a filesystem the image built, so the host's architecture-specific artifacts never enter.
- **`rebuild` handles the case bind mounts cannot.** A changed lockfile needs an image rebuild, not a file copy. With a bind mount you notice by having something break oddly.
- **It is much faster on macOS and Windows**, where bind-mounted filesystems go through a virtualization layer and large `node_modules` trees are slow to the point of being unusable.
- **`ignore` is per-rule**, so build output and dependency directories stay out without touching `.dockerignore`.

**The costs, honestly:** it requires a reasonably current Compose (v2.22+), it is one-directional — a file the container writes does not appear on the host, which breaks workflows that generate code or migrations inside the container — and `docker compose up` alone does not activate it, so a developer who runs the familiar command gets no sync and no error. Say which command the project expects.

Use `develop.watch` for a new stack. Keep an existing, working bind mount unless someone is actually being slowed down by it — see the repair rule in [SKILL.md](SKILL.md).

---

## Profiles — optional services

```yaml
services:
  mailpit:
    image: axllent/mailpit
    profiles: ["tools"]
  jaeger:
    image: jaegertracing/all-in-one
    profiles: ["observability"]
```

A service with a profile **does not start** unless the profile is requested:

```bash
docker compose up                                  # core services only
docker compose --profile tools up                  # plus mailpit
COMPOSE_PROFILES=tools,observability docker compose up
```

This is the right home for anything genuinely optional — an admin UI, a tracing backend, a seeder. It beats commenting services out, because a commented service drifts and a profiled one is still validated by `docker compose config`.

**Careful:** if a core service `depends_on` a profiled one, the dependency silently doesn't start and the gate can't be satisfied. Dependencies of core services do not belong behind a profile.

---

## Writing `.env.example`

This file is the difference between `git clone && docker compose up` working and a new developer losing an afternoon. **Every variable gets a comment.** A bare `API_KEY=` tells nobody where to get one.

```bash
# ── Database ────────────────────────────────────────────────
# Local only. Production credentials come from the secret store.
POSTGRES_USER=app
POSTGRES_PASSWORD=localdev
POSTGRES_DB=app_development
# Used by the app and by the migration container. Host is the
# compose service name, not localhost.
DATABASE_URL=postgresql://app:localdev@postgres:5432/app_development

# ── Redis ───────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── Application ─────────────────────────────────────────────
NODE_ENV=development
PORT=3000
# Any non-empty string works locally. Generate with:
#   openssl rand -hex 32
SESSION_SECRET=change-me-locally

# ── Third-party (optional) ──────────────────────────────────
# Leave blank to disable payments locally; the app falls back
# to a stub. Test keys: https://dashboard.stripe.com/test/apikeys
STRIPE_SECRET_KEY=
```

Four things that make it work:

1. **Grouped by service**, in the order someone will need them.
2. **Dev-only values labelled dev-only.** `localdev` is fine; what's not fine is a value that looks production-plausible and gets copied.
3. **The connection strings use service names**, so they're correct as written rather than needing a fix nobody documents.
4. **Optional variables say what happens when they're blank.** Otherwise everyone stops to hunt a Stripe key they don't need.

**Verify `.env` is gitignored** rather than assuming it. The whole scheme fails silently and permanently if it isn't, and the failure is only discovered by someone reading your repository.

---

## Interpolation

| Form | Behavior |
|---|---|
| `${VAR}` | Empty if unset — silent, and usually the wrong choice |
| `${VAR:-default}` | Default if unset **or empty** |
| `${VAR-default}` | Default only if **unset** (an empty value stays empty) |
| `${VAR:?message}` | **Fail with the message** if unset or empty |
| `$$` | A literal `$` — needed for shell variables in a `command` |

**Use `:?` for anything with no safe default.** A database password interpolating to empty starts a Postgres that accepts anything, which is a worse outcome than a failed `up`.

`docker compose config` renders the whole file with interpolation applied. Run it first — it catches a missing variable in a second rather than in a confusing runtime failure. Note that it also prints the resolved values, so don't paste its output anywhere public.

---

## Secrets

For local development, a gitignored `.env` is a reasonable boundary. Two limits worth knowing:

- **`environment:` values are visible** to `docker inspect` and to any process that can read `/proc/<pid>/environ` in the container.
- **They land in shell history and CI logs** when passed on a command line.

For anything beyond a laptop, compose supports file-backed secrets mounted at `/run/secrets/<name>`:

```yaml
services:
  api:
    secrets:
      - db_password
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

The app reads the file rather than the variable — a pattern worth adopting if the same code will run under Kubernetes or Swarm, both of which mount secrets the same way. Many images support it natively: Postgres accepts `POSTGRES_PASSWORD_FILE`, MySQL `MYSQL_PASSWORD_FILE`.

**The honest limit:** `secrets.file` is still a file on disk in your repo directory, so it must be gitignored exactly like `.env`. It is better than an env var, not a secret manager. Once this stack leaves laptops, the values belong in whatever the platform provides.

---

## Where the dev/prod line actually sits

Compose is excellent at reproducing a **local** environment and is not a deployment tool. The things that make a production stack production — rolling updates, replica scheduling, real secret storage, autoscaling, cross-host networking — are not compose's job, and approximating them here produces a file that is both a bad deployment manifest and a confusing dev environment.

Reasonable to configure here:

- Image versions matching production's majors
- The same service topology
- Health gates
- Resource limits, **if** the point is to catch a memory leak locally

Not reasonable here:

- `deploy.replicas`, rolling update policies
- Production secret backends
- TLS termination and real certificates
- Anything whose only purpose is to look like production without being it

A local environment that's correct in its *shape* — same engines, same majors, same startup dependencies — catches the bugs you can catch locally. Making it look like production in the ways that don't matter does not catch more, and costs everyone startup time on every boot.
