---
name: docker-compose
description: Generate a Docker Compose stack for this repo — app services detected from the source, plus the databases, caches, queues and search engines it actually connects to — with named volumes, an isolated network, health gates, a .env.example and a dev override. Use when a repo needs a one-command local environment, or when an existing compose file starts up in the wrong order or loses its data.
---

# 🧩 Docker Compose

## Where this fits

The container skills:

1. [dockerfile](../dockerfile/SKILL.md) — one image per service, plus the `.dockerignore` that defines its build context
2. **docker-compose** (this skill) — wires those images to datastores, networks, volumes and health gates
3. [container-hardening](../container-hardening/SKILL.md) — reviews how containers run in production. When a compose file *is* the production deploy (a VM running `docker compose up -d`), it gets that full review; a dev stack built here is only checked for what hurts the laptop
4. [container-debug](../container-debug/SKILL.md) — when a container won't start, stay up or connect: reads the runtime's own record, matches the symptom, proves the cause, and routes the fix back to the skill that owns it
5. [docker-swarm](../docker-swarm/SKILL.md) — reviews or designs a Swarm cluster and the stack files `docker stack deploy` runs

**Run [dockerfile](../dockerfile/SKILL.md) first.** Compose orchestrates images; it cannot repair one. Most "compose is broken" reports are an image that doesn't start, doesn't answer its healthcheck, or dies on `SIGTERM` — and no amount of compose configuration fixes any of those.

It leans on two reference docs:

- [service-catalog.md](service-catalog.md) — per-service definitions: image, healthcheck, volume path, env vars, connection string
- [environments.md](environments.md) — `.env` vs `.env.example`, override files, secret handling, dev/prod divergence

---

## 📐 Calibrate the pass

Say which you picked:

- **Greenfield** — no compose file. Work Steps 1–5 in order.
- **Repair** — a compose file exists and something is wrong (startup races, data lost on `down`, ports colliding, a service that can't reach another). **Reproduce the failure and name it before editing.** Rewriting a compose file that mostly works is how a local environment that was merely annoying becomes broken. Read it for the settings in Step 2's "never in the base" list as well, whatever the reported problem is, and name any you find.
- **Add a service** — the stack exists and needs one more. Read the existing conventions (network name, volume naming, env var style) and match them. Consistency inside the file beats correctness imported from elsewhere.

---

## 🔍 Step 1: Detect what the app actually connects to

Do not compose a stack from what the framework usually needs. Compose it from what **this repo's code and config** reach for. The evidence, in descending order of reliability:

- [ ] **Connection strings and client constructors in the source** — `DATABASE_URL`, `REDIS_URL`, a `psycopg` connect, a `new Redis(...)`, an Elasticsearch client, an AMQP dial. This is the ground truth: a dependency the code opens a socket to is a service; anything else is a guess.
- [ ] **The ORM / migration config** — `alembic.ini`, `prisma/schema.prisma` (its `provider` names the engine exactly), `config/database.yml`, `ormconfig`, `knexfile`. These name the engine and often the version.
- [ ] **Dependency manifests** — a `pg` / `psycopg2` / `mysql2` / `mongoose` / `redis` / `amqplib` / `kafkajs` / `meilisearch` client in the lockfile is strong evidence.
- [ ] **Existing env templates and CI service definitions** — `.env.example`, a `services:` block in a GitHub Actions workflow. CI usually already declares the real answer, including versions.
- [ ] **An existing compose file** anywhere in the tree, including a partial one.

Then state the inference before writing anything:

> **Services:** api (Node 20, Dockerfile present, port 3000) · postgres 16 (from `prisma/schema.prisma`, `DATABASE_URL`) · redis 7 (from `REDIS_URL`, used for sessions and the BullMQ queue) · worker (same image as api, different command — from `src/worker.ts`)
> **Not included:** S3 (code points at real AWS; no local substitute requested)

**Two failure modes to avoid, in both directions.** Adding a service the code never uses gives everyone a slower, heavier environment for nothing. Missing one means the stack starts and the app fails on first request. The second is more common when you infer from the framework instead of from the source.

**Pin every version**, and match production. `postgres:16-alpine`, not `postgres:latest`. A local environment on a different major than production is a source of bugs that only appear after deploy — which is exactly the class of bug this file exists to prevent.

---

## 🧱 Step 2: Write the services

For each service, the definitions in [service-catalog.md](service-catalog.md) give a correct starting point — image, healthcheck, volume path, env vars, connection string.

**App services:**

- [ ] `build:` with `context` and `dockerfile` for services this repo owns; `image:` for third-party ones.
- [ ] `environment:` reading from the `.env` via `${VAR}` interpolation — **not literal values**, and never a literal secret.
- [ ] `ports:` only for services a human or an external tool needs to reach. Service-to-service traffic uses the network and needs no published port. **Every published port is a port that can collide with another project**, so publish deliberately.
- [ ] `depends_on:` with `condition: service_healthy` — see Step 3.
- [ ] `restart: unless-stopped` for anything long-running. It restarts a container that **exits**; one that hangs and fails its healthcheck stays up and `unhealthy`, because plain Docker acts on nothing but exit.
- [ ] **Never in the base, and flagged in repair:** `privileged: true`, `pid: host`, `network_mode: host`, `cap_add` of `SYS_ADMIN`/`SYS_PTRACE`/`NET_ADMIN`/`SYS_MODULE`, bind mounts of `/`, `/etc`, `/proc`, `/sys` or `$HOME`, and a mounted `/var/run/docker.sock` (socket access is root on the host; `:ro` doesn't restrict the API). The host here is a developer's laptop. Where a dev tool genuinely needs one — `docker:dind` needs `privileged`, Traefik needs the socket — it goes behind a `profiles:` entry in the override with a comment naming the risk.
- [ ] Source syncing for development **only in the override file**, never in the base — see Step 5. Prefer `develop.watch` over a bind mount on anything new: it copies changed files into the image's own filesystem instead of shadowing it, so the host's architecture-specific `node_modules` never enters the container, and it can rebuild on a lockfile change. [environments.md](environments.md) has both patterns and the version requirement.

**Backing services:**

- [ ] Pinned image, matching production's major version.
- [ ] A **named volume** on the data directory — Step 4.
- [ ] A healthcheck that proves readiness, not liveness — Step 3.
- [ ] Credentials via `${VAR}` from the env file, with a dev-only default.

**One network, explicitly declared.** Compose already puts every service on a project-scoped `<project>_default` network with DNS by service name, so the explicit `networks:` block buys **visibility**, not isolation — it names the boundary in the file, and it is the place to split a `backend` network off later if the local stack has to mirror a real segmentation boundary. (Docker's *default bridge*, the one `docker run` uses without `--network`, is different: no DNS by name, which is why a container started by hand can't find `postgres`.) Services reach each other by **service name** — `postgres:5432`, not `localhost:5432`. Getting that wrong is the most common connection failure in a first compose file, because the string that works on the host doesn't work inside the network.

**Pin the project name** with a top-level `name:`. It otherwise comes from the directory, so two checkouts or worktrees both called `app` share — and clobber — each other's volumes.

---

## ❤️ Step 3: Health gates, not hope

`depends_on` **without a condition only waits for the container to start**, not for the service inside it to be ready. Postgres accepts a TCP connection several seconds before it will accept a query. So the plain form guarantees nothing, and the symptom is an app that crashes on boot roughly one time in three — the flakiest possible failure, and the one most often "fixed" with a sleep.

```yaml
depends_on:
  postgres:
    condition: service_healthy
  redis:
    condition: service_started
```

- [ ] **Every backing service has a healthcheck that runs a real query**, not a port check. `pg_isready`, `redis-cli ping`, `mongosh --eval`, an HTTP `/_cluster/health`. [service-catalog.md](service-catalog.md) has the correct probe per service.
- [ ] **`start_period` is set** on anything slow to boot (Elasticsearch, Kafka, a database restoring a volume). Failures during it don't count against `retries`, which is what stops a slow starter from being killed before it ever comes up.
- [ ] **`condition: service_completed_successfully`** for one-shot dependencies — a migration container the app must not start before.
- [ ] **The app still retries its own connections.** A health gate fixes startup order; it does not fix a database that restarts at 3am. Compose ordering is a convenience, not a substitute for reconnect logic, and treating it as one produces an app that only works when nothing has ever failed.

---

## 💾 Step 4: Volumes — named, not bind

- [ ] **Every stateful service has a named volume** on its data directory. Without one, the data goes into an anonymous volume the image declares, `docker compose down` orphans it, and the next `up` starts on an empty database. People discover this by losing a seeded dev database — it is recoverable from `docker volume ls -f dangling=true` until someone prunes, and entirely preventable by one line.
- [ ] **Named volumes for data, bind mounts for source.** A bind mount for Postgres data hits permission and performance problems on macOS and Windows; a named volume for source code means your edits don't show up.
- [ ] **Declare them in the top-level `volumes:` block** so they're namespaced to the project and `docker compose down -v` can remove them deliberately.
- [ ] **Seed and init data** mounts read-only at the container's init path (`/docker-entrypoint-initdb.d` on Postgres and MySQL) — it runs once, on an empty data directory only.

Say out loud which volumes hold data a developer would be upset to lose, and that `down -v` deletes them. That's the one destructive command in this stack's daily use.

---

## 🔐 Step 5: `.env.example` and the override

- [ ] **`.env.example` lists every variable** the stack reads, **with a comment per variable** saying what it's for and what a safe local value looks like. It is committed. It is the file that makes `git clone && docker compose up` work for someone who has never seen the project.
- [ ] **`.env` is gitignored** — verify this rather than assuming it, because the whole scheme fails silently and permanently if it isn't.
- [ ] **Dev-only defaults are marked as such.** `POSTGRES_PASSWORD=localdev` is fine and should say `# local only — production uses the secret store`. A default that looks production-plausible is how a weak password reaches production.
- [ ] **`docker-compose.override.yml` carries the dev-only parts** — source syncing, a hot-reload command, debugger ports, published database ports. Compose loads it automatically, so `up` is the dev experience and `-f docker-compose.yml` alone is the clean one. **Keep the base file deployable** — meaning it runs clean without the override; a base with a bind mount over `/app` doesn't. It does not mean Swarm-ready: `docker stack deploy` ignores `build:` and `depends_on`, and [environments.md](environments.md#if-the-same-file-goes-to-docker-stack-deploy) has the full list.
- [ ] **Published ports bind to loopback**: `"127.0.0.1:5432:5432"`. The short form listens on every interface of the laptop, and Docker's firewall rules bypass `ufw` to do it.

[environments.md](environments.md) covers the override mechanics, the merge rules that surprise people (lists append, scalars replace), and where secrets go once this leaves a laptop.

---

## ✅ Step 6: Verify

Every claim here has a command behind it:

- [ ] **`docker compose config`** — renders and validates. Catches interpolation typos and a missing `.env` var before anything starts.
- [ ] **`docker compose up -d`** from a **clean state** (`down -v` first). The startup race only reproduces on a cold start with empty volumes; a warm start hides it.
- [ ] **Every service is healthy** — `docker compose ps -a` shows `healthy`, not just `running`, and every one-shot service shows `Exited (0)`. Without `-a`, an exited migration container — the one that failed — isn't listed at all.
- [ ] **The app answers.** Hit its port and get a real response, not just an open socket.
- [ ] **The app reached its dependencies** — `docker compose logs app` shows a successful connection, no retry storm.
- [ ] **Data survives the containers** — write something, `docker compose down` (**no** `-v`), `docker compose up -d`, read it back. This is the check that proves the volume is real. **`docker compose restart` proves nothing**: it reuses the same container, whose writable layer survives a restart with no volume at all.
- [ ] **It works from cold twice.** `down -v && up -d`, twice. A startup race that appears one run in three is still a broken file, and a single green run is not evidence.

When a check fails, the moves that find out why:

| Symptom | Look with |
|---|---|
| A service exited | `docker compose ps -a` for the exit code, `docker compose logs --tail=100 <svc>` |
| Exit `137` | `docker inspect -f '{{.State.OOMKilled}}' <container>` — `true` is a memory limit, `false` a kill after the stop timeout |
| Crash-looping, `exec` refused | `docker compose run --rm --entrypoint sh <svc>` — a fresh container you can look around in |
| `no such host` for a service name | `docker compose exec <svc> getent hosts <other>`; the two aren't on a common network, or the other isn't running |
| `connection refused` | The target is up but not listening yet — a missing health gate, or the app not retrying |
| An edit to the compose file had no effect | `restart` doesn't re-read the file; `docker compose up -d` does |
| Old dependencies after a rebuild | Anonymous volumes carried over — `docker compose up --build -V` |
| Healthcheck failing | `docker inspect -f '{{json .State.Health}}' <container>` shows the probe's own output |

---

## 🛑 Stopping rule

Stop when all four hold:

- [ ] Every Step 6 check passes, each with its observed result stated.
- [ ] **Every service in the file is one the app actually connects to** — nothing composed speculatively.
- [ ] **`.env.example` is complete** — a clean clone starts with no undocumented variable.
- [ ] Anything left undone is **recorded with its reason** — a cloud service with no local substitute, a licensed image, a dependency deliberately left pointed at staging.

Then stop. **Compose is a local development tool, and hardening it past that is effort spent on the wrong artifact.** Resource limits, replica counts, secret backends, restart policies tuned for production, `read_only` root filesystems and dropped capabilities belong in whatever actually runs production — the [dockerfile](../dockerfile/SKILL.md) skill's "survives runtime hardening" check is where an image proves it can take them, and [container-hardening](../container-hardening/SKILL.md) is where a production deployment gets reviewed for them. A compose file that tries to be a deployment manifest ends up being a bad one and a confusing dev environment at the same time.

---

## Subagents — optional

Worth it when **Step 1 spans a large monorepo** — dispatch one subagent per service directory to infer that service's dependencies from its source, read-only, returning the inference block above.

**Steps 2–6 do not delegate.** The whole point of a compose file is the relationships *between* services — one network, one env file, shared health gates, service names that must match connection strings on both sides. Split that across agents and you get services that each look right and don't talk to each other. Verification is a write plus a running stack, which two agents cannot share.

**Dispatch contract.** A subagent starts with no history. Give each one the **prior**, the **target** (which service directory it owns, and that the others are covered so it neither duplicates nor apologises for the gap), the **context it cannot infer** (production's versions, which dependencies are deliberately cloud-only), the **return shape** — the Step 1 inference block including "none found" so a silent delegate is distinguishable from a clean read — and an explicit *"report conclusions, not file excerpts."* Delegates stay **read-only**.

---

## Rules of Engagement

1. **Compose what the code connects to.** Evidence from the source, not from what the framework usually pairs with.
2. **Pin every image, and match production's major.** `latest` is not a version, and a version skew local-to-prod defeats the purpose of the file.
3. **Health gates, not sleeps.** A `sleep 10` in an entrypoint is a race you've decided to lose more slowly.
4. **Named volumes on everything stateful.** `down` must not be able to destroy a developer's data by accident.
5. **No literal secret in the file.** `${VAR}` from a gitignored `.env`, with the template committed.
6. **Verify from cold, twice.** Warm starts hide exactly the bug this file is most likely to have.
7. **The laptop is a host too.** Nothing in the base gets root on it — no privileged containers, no host namespaces, no Docker socket — and nothing listens beyond loopback.

## Handoff

Once the stack comes up clean twice:

> The stack is up: `<n>` services, all healthy from cold, data surviving a restart. `.env.example` documents `<m>` variables. Start it with `docker compose up -d`; **`docker compose down -v` deletes the volumes**, including the database.

If this stack was built to support a feature rather than to stand alone, the next step is back in the build pipeline — [tdd](../../development/tdd/SKILL.md) can now run its suite against real backing services instead of mocks, which is worth saying out loud since it changes what the tests are allowed to assume.
