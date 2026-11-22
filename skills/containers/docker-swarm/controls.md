# Controls — Seven Domains

**Contents:** 1. cluster · 2. rollout · 3. state · 4. network · 5. secrets · 6. scheduling · 7. stack file

> The criteria Review grades against and Design satisfies. Each domain has 🟢 what good looks like,
> 🔴 the anti-patterns (**What / Why / Detect / Fix / Severity**), and the **Checklist** whose criteria
> are scored proportionally per [`scoring.md`](scoring.md). Every 🔴 names its principle in
> [`theory.md`](theory.md). Read each service in context — a grep match is a candidate, not a finding.
>
> In scope: **cluster** — the one cluster (or each, if several); **network**, **rollout**, **state**,
> **secrets**, **scheduling** — services; **stack file** — stack files and the deploy command that
> reads them.

---

## 1. cluster — managers, quorum and the control plane

### 🟢 Well done
- 3 or 5 managers, odd, in one region on static addresses (S2).
- Managers drained (`availability: drain`) or deliberately shared with a written reason (S12).
- Autolock on, the unlock key in a password manager or vault outside the cluster (S12).
- `/var/lib/docker/swarm` backed up from a non-leader, restore rehearsed (S12).
- Ports 2377, 7946, 4789 open only between nodes; address pool clear of the VPC (S9).

### 🔴 Not well done

#### Even or single manager count
**What:** 1, 2 or 4 managers (`docker node ls` shows `Leader` + `Reachable` rows).
**Why:** Two managers tolerate **zero** losses — the same as one — and double the chance of losing
quorum, because either one failing stops the control plane; four tolerate one, the same as three
(S2).
**Detect:** captured or live `docker node ls`. ✅ when observed; 🔬 otherwise.
**Fix:** promote or add to 3 (or demote to 1 deliberately for a non-production cluster).
**Severity:** Critical for two managers in production (the README usually claims "HA"); High for one
manager in production; Medium for four.

#### Managers carry workloads
**What:** managers `Active` and running application tasks, with no reservations on those tasks.
**Why:** A memory-hungry task starves Raft; a noisy neighbour on a manager is a control-plane outage
(S12).
**Detect:** `docker node ls` availability; `docker node ps <manager>`. ✅ / 🔬.
**Fix:** `availability: drain` on managers, or reservations on every task and a node label keeping
heavy services off them.
**Severity:** Medium; High with no reservations anywhere.

#### No autolock, no backup
**What:** `docker info` shows autolock off; no backup job for `/var/lib/docker/swarm`; no restore drill.
**Why:** A stolen manager disk is the cluster's keys; losing quorum with no backup is rebuilding every
service, secret and network from scratch (S12).
**Detect:** `docker info --format '{{.Swarm.Cluster.Spec.EncryptionConfig.AutoLockManagers}}'` on a
manager; backup scripts in the repo. ⚠️ / 🔬.
**Severity:** Medium each; High together in production.

#### Overlay ports and address pool unplanned
**What:** no record of 2377/7946/4789 between nodes; overlays on the default `10.0.0.0/8` pool in a
VPC that overlaps it; a cloud that reserves 4789.
**Why:** Overlays that silently can't reach peers, or routes that collide with the VPC (S9).
**Detect:** IaC or firewall config; `docker network inspect` subnets. ⚠️ / 🔬.
**Severity:** Medium.

### Checklist
- [ ] odd manager count, 3 or 5 · [ ] managers drained or reserved · [ ] autolock on, key stored
  outside · [ ] swarm state backed up, restore rehearsed · [ ] overlay ports and pool planned

---

## 2. rollout — how a change reaches production, and how it's undone

### 🟢 Well done
- A healthcheck on every service — in the image or the stack (S4).
- `update_config`: `parallelism` sized to capacity, `delay`, `order: start-first` where there's room,
  `failure_action: rollback`, `monitor` longer than `start_period + interval × retries`,
  `max_failure_ratio` stated (S4).
- `rollback_config` set (often `parallelism: 0` — all at once — and `order: stop-first`) and
  rehearsed (S4).
- `restart_policy: {condition: on-failure, delay, max_attempts, window}` (S5).

### 🔴 Not well done

#### Default update config in production
**What:** no `update_config`, or one missing `failure_action`/`order`/`monitor`.
**Why:** The default **pauses** a failed update half-way — half the tasks on the new version, half on
the old, nobody told — and stops the old task before the new one is healthy (S3, S4).
**Detect:** stack file; `docker service inspect --format '{{json .Spec.UpdateConfig}}'`. ✅.
**Fix:** the 🟢 block above.
**Severity:** High on a production service; Medium elsewhere.

#### No healthcheck
**What:** neither the image (`HEALTHCHECK`) nor the stack (`healthcheck:`) defines one, or it's
`disable: true`.
**Why:** Swarm can then detect only a task that crashes; a release that starts and serves errors rolls
out to every replica (S4).
**Detect:** stack file; the Dockerfile; `docker inspect` of the image's `Config.Healthcheck`. ✅ when
the Dockerfile is in the repo, ⚠️ for third-party images.
**Fix:** a cheap local endpoint check (to [dockerfile](../dockerfile/SKILL.md) for the image, or a
stack `healthcheck:`).
**Severity:** High; Critical in the chain "no healthcheck + default update config" on the edge service.

#### Monitor shorter than the healthcheck
**What:** `monitor` (default 5 s) less than `start_period + interval × retries`.
**Why:** The update is declared successful before the healthcheck could have failed (S4).
**Detect:** arithmetic from the stack and the healthcheck. ✅.
**Severity:** Medium; High when `failure_action: rollback` is the only safety net.

#### Unbounded restarts
**What:** no `restart_policy`, or `condition: any` with no `max_attempts`.
**Why:** A bad config crash-loops forever, flooding logs and churning the scheduler (S5).
**Detect:** stack file. ✅.
**Severity:** Medium.

#### Rollback never exercised
**What:** no record of a rollback drill; no `rollback_config`.
**Why:** The first rollback runs during the incident it was meant to shorten (S4).
**Detect:** runbooks, CI. ⚠️.
**Severity:** Medium.

### Checklist
- [ ] every service healthchecked · [ ] update config rolls back on failure · [ ] monitor outlasts the
  healthcheck · [ ] rollback config set and rehearsed · [ ] restarts bounded

---

## 3. state — where data lives

### 🟢 Well done
- Each stateful service pinned (`node.labels.<x> == true` or `node.hostname == …`) to the node holding
  its volume, `replicas: 1` unless the software replicates itself (S7).
- A backup and a tested restore for each volume; or the datastore kept off the cluster (managed DB) (S7).

### 🔴 Not well done

#### Replicated single-writer datastore
**What:** `replicas: 2+` (or `mode: global`) on Postgres, MySQL, MariaDB, MongoDB without a replica set,
Redis without replication, SQLite-backed apps — on `local` volumes.
**Why:** Each replica gets its own empty volume on its own node: two diverging databases behind one
VIP, and the app sees whichever one a connection lands on (S7).
**Detect:** stack file: datastore image + `replicas` > 1. ✅.
**Fix:** `replicas: 1` + a placement constraint; replication, if needed, by the database's own
mechanism with one service per member.
**Severity:** Critical.

#### Stateful service with no placement constraint
**What:** a service with a named `local` volume and no `placement.constraints`.
**Why:** A node drain, failure or rebalance reschedules it elsewhere with an empty volume — the data
"disappears" and the old copy sits orphaned on the old node (S7).
**Detect:** stack file. ✅.
**Fix:** a node label and a constraint.
**Severity:** High; Critical for a primary datastore.

#### Shared volume without coordination
**What:** a shared volume driver (NFS, a cloud volume plugin) mounted by several writers that don't
coordinate.
**Why:** Concurrent writers corrupt files (S7).
**Detect:** stack file `driver:`/`driver_opts`; the app's design. ⚠️.
**Severity:** High.

### Checklist
- [ ] no replicated single-writer datastore · [ ] every stateful service pinned · [ ] every volume has a
  backup and a restore

---

## 4. network — overlays, the mesh, exposure

### 🟢 Well done
- One overlay per tier; datastores only on the backend overlay (S9).
- `encrypted: "true"` on overlays carrying sensitive cross-host traffic (S9).
- Only edge services publish; `mode: host` where the client IP matters or a global service binds per
  node (S8).

### 🔴 Not well done

#### Client IP lost behind the mesh
**What:** a service that rate-limits, geo-filters, allow-lists or audit-logs by client IP, published in
the default ingress mode.
**Why:** The mesh rewrites the source address, so every client looks like an internal address — a
rate limit by IP becomes one shared bucket, an allow-list lets everyone or no one through (S8).
**Detect:** app or proxy config (`limit_req_zone $remote_addr`, `X-Forwarded-For` trust, rate-limit
middleware) + `ports:` without `mode: host`. ✅.
**Fix:** `ports: [{target: 443, published: 443, mode: host}]` on a global edge service (or a load
balancer that sends PROXY protocol); trust `X-Forwarded-For` only from it.
**Severity:** High.

#### Internal service published
**What:** a datastore, admin UI or internal API with `ports:`.
**Why:** The mesh opens it on every node, on every interface (S8).
**Detect:** stack file. ✅.
**Severity:** High; Critical for a datastore with a weak credential.

#### Flat or unencrypted overlay
**What:** all services on one overlay; sensitive traffic across hosts on an overlay without
`encrypted`.
**Why:** A compromised edge reaches the database directly; overlay payloads cross the network in
clear (S9).
**Detect:** stack file `networks:`. ✅.
**Severity:** Medium; High when payment or personal data crosses hosts in clear.

#### `dnsrr` with published ports
**What:** `endpoint_mode: dnsrr` on a service with ingress-mode ports.
**Why:** Invalid — the deploy fails (S8).
**Severity:** High (it won't deploy).

### Checklist
- [ ] only edge services published · [ ] client-IP-dependent services use host mode or PROXY protocol ·
  [ ] tiers on separate overlays · [ ] sensitive overlays encrypted

---

## 5. secrets — credentials and configuration

### 🟢 Well done
- `external: true` secrets created from stdin (`printf %s "$V" | docker secret create name_v1 -`),
  versioned names, mounted with `uid/gid/mode: 0400`, read through `*_FILE` (S11).
- Configs for non-secret files, also versioned (`name: app_cfg_${CFG_VERSION}`) (S11).

### 🔴 Not well done

#### Secret file committed
**What:** `secrets: <x>: file: ./secrets/…` where that file is in the repo.
**Why:** The value is in git history forever; anyone with the repo has it (S11).
**Detect:** stack file + `git ls-files` of the path. ✅. **Kind and location only — never the value.**
**Fix:** **rotate** — new secret `name_v2` from stdin, swap the service, revoke the old credential at
its source — then remove the file and `.gitignore` the directory.
**Severity:** Critical for a production credential.

#### Secret as an environment variable
**What:** credentials in `environment:`, including `${VAR}` interpolation.
**Why:** Visible in `docker service inspect` and to every child process; also in the deploying shell's
history (S11).
**Detect:** stack file. ✅.
**Severity:** Medium; High for production database or payment credentials.

#### Rotation by mutation
**What:** a runbook that "updates" a secret or config in place, or a deploy that fails with "only updates
to Labels are allowed".
**Why:** Secrets and configs are immutable; the only rotation is a new name (S11).
**Severity:** Low (it fails loudly) — but note it.

### Checklist
- [ ] no secret source committed · [ ] secrets external or file-sourced from outside the repo ·
  [ ] secrets as files, not env · [ ] versioned names for rotation

---

## 6. scheduling — placement, resources, images

### 🟢 Well done
- Reservations and limits on every production service (S10).
- Replicas spread: `placement.preferences: [spread: node.labels.zone]`, `max_replicas_per_node` (S10).
- Images by digest from a registry every node reaches, deployed with `--with-registry-auth` (S6).

### 🔴 Not well done

#### Mutable images
**What:** `:latest`, no tag, or tag-only in a production stack.
**Why:** Two deploys of the same file run different code; S6.
**Detect:** stack file. ✅.
**Severity:** High for `latest`/untagged; Medium for tag-only.

#### No reservations or limits
**What:** no `deploy.resources`.
**Why:** The scheduler packs blindly; one leak takes a node, and the rescheduled tasks take the next
(S10).
**Detect:** stack file. ✅.
**Severity:** Medium; High when managers run workloads.

#### All replicas can share one node
**What:** `replicas: 2+` with no spread preference, no `max_replicas_per_node`, few nodes.
**Why:** One node loss takes the whole service (S10).
**Detect:** stack file; `docker service ps` placement. ✅ / ⚠️.
**Severity:** Medium.

#### Private registry without credentials
**What:** a private image and a deploy command without `--with-registry-auth`.
**Why:** Workers can't pull; tasks stay `Rejected` / `No such image` (S6).
**Detect:** deploy script. ✅.
**Severity:** High (deploys fail on some nodes).

### Checklist
- [ ] every image pinned by digest · [ ] reservations and limits set · [ ] replicas spread across nodes ·
  [ ] registry auth passed to the deploy

---

## 7. stack file — what `docker stack deploy` actually reads

### 🟢 Well done
- A stack file separate from the dev Compose file, with no keys stack deploy ignores (S3).
- Variables supplied by the deploying environment (CI), and `docker stack config -c stack.yml`
  rendering cleanly as the step before deploy (S3).
- One deploy command, from CI, from the versioned file; no manual `service` commands (S1).

### 🔴 Not well done

#### Relying on keys stack deploy ignores
**What:** `depends_on` (especially with `condition: service_healthy`), `restart`, `build`,
`container_name`, `links`, `network_mode`, `privileged`, `devices`, `security_opt`, `cap_add` on old
engines — used as if they work.
**Why:** They don't: no startup order, no build, no privilege change. A team that believes the API
waits for a healthy database has an API that crashes on boot and is restarted until the database is
up (S3).
**Detect:** stack file + README or comments describing the ordering. ✅. Note the asymmetry: the
**list** form (`depends_on: [postgres]`) is accepted and ignored; the **long** form with
`condition: service_healthy` is rejected by the stack schema ("must be a list"), so that file doesn't
deploy at all.
**Fix:** connection retries in the app; healthchecks plus `restart_policy`; push images in CI.
**Severity:** High when the README or design relies on it; Low when it's dead config.

#### `.env` assumed
**What:** `${VAR}` interpolation with a `.env` file beside the stack, and a deploy that doesn't export
the variables.
**Why:** `docker stack deploy` doesn't read `.env`: unset variables render as empty strings — an
empty image tag, an empty password (S3).
**Detect:** stack file `${…}` + deploy script that doesn't `set -a; . ./.env` or export from CI. ✅.
**Fix:** export from CI, or `set -a; . ./.env; set +a` in the deploy script deliberately; `${VAR:?}` so
missing values fail. `docker stack config -c stack.yml` run **without** the variables shows the damage —
`image: 'registry.example.com/app:'` with an empty tag, empty settings.
**Severity:** High.

#### Imperative drift
**What:** runbooks or scripts with `docker service scale`, `service update --image`, `--replicas`.
**Why:** Reverted by the next deploy, or the stack file stops describing production (S1).
**Detect:** scripts, docs. ✅.
**Severity:** Medium.

#### `--prune` surprise
**What:** `--prune` in the deploy with services deployed from more than one file or by hand.
**Why:** Anything not in this file is deleted on deploy (S1).
**Severity:** Medium.

### Checklist
- [ ] no relied-on ignored keys · [ ] variables come from the deploy environment, not `.env` ·
  [ ] `docker stack config` validates before deploy · [ ] the stack file is the only source of truth
