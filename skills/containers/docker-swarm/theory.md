# Theory — The Principles Every Swarm Finding Cites (S1–S12)

**Contents:** Part A: How Swarm works · Part B: Changing a running system · Part C: State, network and placement · Part D: Secrets and the cluster itself

> Every finding in a review names one of these. Each principle states **what it says**, **why it
> matters** for a Swarm cluster, and **what violating it looks like** in a stack file or a cluster.
> Sources:
>
> | Short name | Source |
> |---|---|
> | **DDD** | Nigel Poulton, *Docker Deep Dive* (2018) — Swarm, overlay networking, stacks, volumes, security, enterprise operations |
> | **DUR** | Sean Kane & Karl Matthias, *Docker: Up & Running*, 2nd ed. (O'Reilly, 2018) — the path to production, Swarm mode |
> | **DIA** | Jeff Nickoloff & Stephen Kuenzli, *Docker in Action*, 2nd ed. (Manning, 2019) — services, stacks, secrets and configs, overlay networks, placement |
> | **HEPIA** | Wade & Mendonça, *Docker, Docker Compose, Swarm* course slides (HEPIA, 2023–24) |
> | **DIGIA** | Valtonen, *A Docker Swarm hands-on* (Digia slides) |
> | **Docs** | Docker's current Swarm mode and Compose file reference documentation |
>
> Chapters, not pages. The three books describe Docker 17–19; Swarm mode has changed little since,
> but some mechanics are newer than them. Where a principle is the book's and the mechanism is
> current practice, the mechanism is marked **(current)**: `docker stack config`, `max_replicas_per_node`,
> `--data-path-port`, `--default-addr-pool`, `cap_add` honoured by services, and the containerd image
> store. Swarm classic, Docker EE / UCP / DTR, Docker Content Trust and Cloudstor are gone and are
> not cited.

---

## Part A — How Swarm works

### S1 — Desired state, reconciled
**Says:** A service is a declaration — image, replicas, networks, constraints — that managers store
and every node's agent reconciles its tasks against; a failed task is replaced, not restarted in
place (DDD ch. 10; DUR ch. 10; DIA ch. 11; HEPIA). The stack file is that declaration, so it must be
the single source of truth: an imperative `docker service scale` or `update` is reverted by the next
`docker stack deploy` (DDD ch. 14).
**Violation:** manual `service scale`/`update` in runbooks or chat history that the stack file
doesn't carry; several stack files or scripts deploying the same service; a deploy script that does
anything but `docker stack deploy` from a versioned file.

### S2 — Quorum is arithmetic
**Says:** Managers replicate the cluster state with Raft; the cluster accepts changes only while a
majority is reachable. N managers tolerate ⌊(N−1)/2⌋ losses: 1 and 2 tolerate none, 3 tolerates one,
5 tolerates two. Seven is the practical ceiling — every write waits on more peers (DDD ch. 10, 16;
DUR ch. 10; DIA ch. 11). Managers want low latency between them: one region, static addresses
(DDD ch. 16). Running tasks survive quorum loss, but nothing is rescheduled, updated or deployed
until it's restored (DDD ch. 16).
**Violation:** two or four managers; one manager in production; managers spread across regions;
managers on dynamic addresses.

### S3 — Effective settings, not written ones
**Says:** What Swarm runs is the stack file plus its defaults, minus the keys it ignores.
`docker stack deploy` drops `build`, `depends_on` (conditions included), `restart`,
`container_name`, `links`, `network_mode`, `privileged`, `devices`, `security_opt` and others, and
does not read `.env` (DDD ch. 14; Docs **(current)**). Defaults matter as much: `update_config`
pauses on failure with a 5-second monitor and stops the old task first; `restart_policy` retries
forever; published ports go through the ingress mesh (DDD ch. 10; DUR ch. 10).
**Violation:** a stack file whose correctness depends on ignored keys; `${VAR}` with only a `.env`
beside it; a review that trusts the file instead of `docker service inspect` (current).

---

## Part B — Changing a running system

### S4 — A rollout must be able to detect failure and undo it
**Says:** A rolling update replaces tasks a few at a time, waits, watches, and acts on failure. It can
only notice what it can observe: a task that fails to start or exits within `monitor`, or — with a
`HEALTHCHECK` — a task that turns unhealthy (DDD ch. 10, 14; DUR ch. 10; DIA ch. 13; HEPIA). So
safe rollouts need a healthcheck, `failure_action: rollback`, a `monitor` window longer than the time
the healthcheck needs to fail (`start_period + interval × retries`), and a tested `rollback_config`.
`order: start-first` keeps capacity during the update where there's room for the extra task
(DUR ch. 10).
**Violation:** default `update_config` (pause, stop-first, 5 s) on a production service; no
healthcheck in the image or the stack; `monitor` shorter than the healthcheck can fail; a rollback
never exercised.

### S5 — Bound the retries
**Says:** A restart policy that retries forever turns a crashing release into a hot loop that floods
logs and the scheduler; a bounded one (`condition: on-failure`, `max_attempts`, `window`) turns it
into a visible failure (DIA ch. 13; DDD ch. 14).
**Violation:** no `restart_policy`; `condition: any` with no `max_attempts` on a service that exits
on bad config.

### S6 — Immutable references
**Says:** Swarm resolves an image tag to a digest at deploy and pins tasks to it (DDD ch. 10). A
mutable tag means two deploys of the same file can run different code, and nodes that pull later
may get something else. Deploy by digest, from a registry every node can reach, passing
credentials with `--with-registry-auth` (DDD ch. 14; HEPIA).
**Violation:** `:latest` or tag-only images in a production stack; images built on one node and never
pushed (`build:` is ignored); private registries without `--with-registry-auth`.

---

## Part C — State, network and placement

### S7 — State is node-local
**Says:** A `local` volume exists on the node where the task ran. A replica scheduled on another node
gets a new, empty volume; two replicas of a single-writer database on local volumes are two
diverging databases (DDD ch. 13; DIA ch. 13; DIGIA). Stateful services are pinned by placement
constraint to the node that holds their data, run as one replica unless the software replicates
itself, and have a stated backup. A shared volume driver needs application-level write
coordination (DDD ch. 13).
**Violation:** `replicas: 2` on Postgres, MySQL, Redis-without-replication; a stateful service with
no placement constraint; "data lost" after a node drain.

### S8 — The routing mesh publishes everywhere and hides the client
**Says:** A port published in the default `ingress` mode is opened on **every** node and load-balanced
by IPVS to any task, which also rewrites the client's source address (DDD ch. 12; DUR ch. 10;
DIA ch. 13). `mode: host` publishes only on nodes that run a task and keeps the client IP, at the
cost of one task per node per port. `endpoint_mode: dnsrr` bypasses the VIP and cannot be combined
with ingress-published ports. Load balancing is per connection, so long-lived keep-alive
connections stick to one task (DIA ch. 13).
**Violation:** a service that rate-limits, logs or allow-lists by client IP behind the mesh; an
internal service published at all; `dnsrr` with ingress ports.

### S9 — Segment and encrypt the overlay
**Says:** Services resolve each other by name only on a shared overlay network; one overlay per tier
keeps a compromised edge service off the database network (DDD ch. 11–12; DIA ch. 13). Control-plane
traffic is mutually authenticated TLS; **application traffic on overlays is not encrypted unless the
network sets `encrypted`** (IPsec, with overhead), and the ingress network is never encrypted
(DDD ch. 12, 15; DIA ch. 13). The overlay needs 2377/tcp, 7946/tcp+udp and 4789/udp between nodes;
`--data-path-port` and `--default-addr-pool` (current) handle clouds that reserve 4789 and address
overlaps.
**Violation:** every service on one overlay; sensitive cross-host traffic on an unencrypted overlay;
"Swarm is secure by default" read as covering application traffic.

### S10 — Reservations decide placement
**Says:** The scheduler places a task only on a node whose free **reservations** cover it; limits cap
what it may use. Without reservations, Swarm packs tasks onto nodes that can't hold them; with
reservations larger than any node, tasks stay `pending` with "no suitable node" (DIA ch. 13; DUR
ch. 10). Placement constraints and preferences spread or pin tasks; `max_replicas_per_node` (current)
stops replicas stacking on one node.
**Violation:** no reservations or limits on production services; all replicas of a service able to
land on one node; constraints on labels no node carries.

---

## Part D — Secrets and the cluster itself

### S11 — Secrets are immutable files
**Says:** Swarm secrets are encrypted in the Raft store, sent only to nodes running a task that uses
them, and mounted on a tmpfs at `/run/secrets/<name>` with the `uid/gid/mode` the stack sets
(DDD ch. 14–15; DIA ch. 12). They are immutable: rotation means creating `name_v2` and swapping the
service to it. Created out of band from stdin and declared `external`, they never touch the repo;
`secrets: file:` uploads a file from the deploying machine, which then has to exist — and be
protected — there. Configs work the same way for non-secret files (DIA ch. 12). Environment variables
leak through `inspect`, child processes and crash dumps (DIA ch. 12).
**Violation:** a committed file behind `secrets: file:`; secrets as environment variables; a secret
"updated" in place; config files baked into images per environment.

### S12 — Protect and recover the control plane
**Says:** Managers hold the cluster's keys and state. Autolock encrypts the Raft keys at rest and
requires an unlock key on restart — which must be stored outside the cluster; join tokens and the
CA rotate; certificates expire on a schedule (90 days by default); managers are drained so a workload
can't starve Raft; `/var/lib/docker/swarm` is backed up from a stopped non-leader manager and the
restore (`swarm init --force-new-cluster`) is rehearsed (DDD ch. 15–16; DUR ch. 10).
**Violation:** autolock off; the unlock key nowhere or only on the managers; no backup of the swarm
directory; managers running application workloads with no reservation; a restore never tried.
