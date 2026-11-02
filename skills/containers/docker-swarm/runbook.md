# Runbook — Read-Only Commands, Failure Modes, the Design Skeleton

> §1 is what a review may run. §2 is what a review **recommends** the team rehearse — every command
> in it changes cluster state, so this skill names them and never runs them unless the user asks for
> that specific command. §3 is the stack file skeleton Design starts from.

---

## 1. Read-only evidence

| Question | Command | Read it for |
|---|---|---|
| Managers and quorum | `docker node ls` | one `Leader`, the rest `Reachable`; an odd count; `Drain` on managers |
| Cluster settings | `docker info --format '{{json .Swarm}}'` | managers, nodes, `ControlAvailable` |
| Autolock | `docker info --format '{{.Swarm.Cluster.Spec.EncryptionConfig.AutoLockManagers}}'` (on a manager) | `true` |
| Cert expiry | `docker info --format '{{.Swarm.Cluster.Spec.CAConfig.NodeCertExpiry}}'` | the rotation period |
| Services at desired count | `docker stack services <stack>` | every `REPLICAS` at `n/n` |
| Why tasks fail or wait | `docker service ps --no-trunc <svc>` | the `ERROR` column: `no suitable node`, `No such image`, `task: non-zero exit` |
| What was applied | `docker service inspect <svc> --format '{{json .Spec}}'` | update/rollback/restart config, placement, resources, endpoint mode — the keys that survived |
| Update outcome | `docker service inspect <svc> --format '{{json .UpdateStatus}}'` | `State`: `completed`, `paused`, `rollback_completed`, `rollback_paused` |
| Image actually running | `docker service inspect <svc> --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'` | `image:tag@sha256:…` |
| Network subnets | `docker network inspect <net> --format '{{json .IPAM.Config}} enc={{index .Options "encrypted"}}'` | no overlap with the VPC; `encrypted` where needed |
| The file as stack deploy reads it | `docker stack config -c stack.yml` (with the deploy's environment) | renders; empty values where a variable was missing. It validates the schema and interpolation only — it still prints `depends_on`, `restart` and the other keys deploy ignores, so it is not a list of what will apply |
| Secrets and configs present | `docker secret ls`, `docker config ls` | **names only** — never `inspect` a secret's data |
| Logs of a service | `docker service logs --tail 100 <svc>` | startup errors across all tasks |

Captured outputs the user supplies count the same as live ones; record the capture's date.

---

## 2. Failure modes and drills

Each row: the symptom, the cause, and the recovery — **for the team to run**, and to rehearse before
go-live.

| Symptom | Cause | Recovery (state-changing — not run by this skill) |
|---|---|---|
| `docker service` / `stack` commands fail with "the swarm does not have a leader"; running tasks keep serving | **Quorum lost**: a majority of managers down | Bring managers back. If they're gone for good: on one surviving manager, `docker swarm init --force-new-cluster --advertise-addr <ip>`, then re-add managers to 3. Rehearse it |
| A restarted manager stays out: "swarm is encrypted and needs to be unlocked" | Autolock on | `docker swarm unlock` with the key. **Lost key**: that manager can't rejoin with its state — remove it and re-add a fresh manager while quorum holds; with no quorum, restore from backup. Store the key outside the cluster |
| Tasks `Pending`, `docker service ps` says `no suitable node (insufficient resources on N nodes)` or `(scheduling constraints not satisfied)` | Reservations larger than any node's free capacity; a constraint on a label no node has | Lower reservations, add capacity, or fix the label (`docker node update --label-add`) |
| Tasks `Rejected`, `No such image` on some nodes | Private registry, deployed without `--with-registry-auth`; image built locally, never pushed | Redeploy with `--with-registry-auth`; push from CI |
| An overlay network is missing on a worker | Overlays are created on a worker lazily, when a task that uses it lands there | Not a fault — schedule a task there, then check |
| An update is stuck half-way: `UpdateStatus.State` = `paused` | Default `failure_action: pause` hit a failing task | `docker service update --rollback <svc>` or fix and redeploy; then set `failure_action: rollback` |
| Service "lost its data" after a drain or node failure | Local volume on the old node, no placement constraint | Pin to the node with the data (`node.labels.db == true`) and redeploy; recover from the orphaned volume on the old node or backup |
| Clients all appear as `10.0.0.x` | Routing mesh SNAT | `mode: host` publishing on the edge, or PROXY protocol from the load balancer |
| Deploy error "only updates to Labels are allowed" | Changing a secret or config in place | New versioned name, swap the service to it |
| A service scaled by hand reverted after deploy | Imperative change; the stack file is the desired state | Put the change in the file |

**Drills to schedule before go-live** — named in the review's summary:

1. **Rollback**: deploy a deliberately broken image tag to staging; expect `UpdateStatus.State` = `rollback_completed` with no manual step.
2. **Manager loss**: stop one manager of three; the cluster keeps accepting changes. Stop a second; it stops accepting changes and running tasks keep serving. Restore.
3. **Node drain**: `docker node update --availability drain <worker>` in staging; every service returns to `n/n` elsewhere — and stateful ones stay put because their constraint pins them.
4. **Backup restore**: restore `/var/lib/docker/swarm` to a scratch manager with `--force-new-cluster`.

---

## 3. Design skeleton

```yaml
# stack.yml — deployed by CI: docker stack config -c stack.yml && docker stack deploy -c stack.yml --with-registry-auth --prune app
services:
  web:
    image: registry.example.com/app/web:1.8.2@sha256:<digest>
    healthcheck:
      test: ["CMD", "/app/healthcheck"]          # cheap, local; Swarm gates the rollout on it
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 20s
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password_v1
    secrets:
      - source: db_password_v1
        mode: 0400
    networks: [frontend, backend]
    ports:
      - {target: 8443, published: 443, mode: host}  # keeps the client IP; one task per node
    deploy:
      mode: global
      placement:
        constraints: [node.labels.edge == true]
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
        failure_action: rollback
        monitor: 60s                              # > start_period + interval × retries
        max_failure_ratio: 0
      rollback_config:
        parallelism: 0
        order: stop-first
      restart_policy: {condition: on-failure, delay: 5s, max_attempts: 3, window: 120s}
      resources:
        reservations: {cpus: "0.25", memory: 256M}
        limits: {cpus: "1", memory: 512M}

  postgres:
    image: postgres:16.4@sha256:<digest>
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password_v1
    secrets: [db_password_v1]
    volumes: [pgdata:/var/lib/postgresql/data]
    networks: [backend]
    deploy:
      replicas: 1                                 # single writer
      placement:
        constraints: [node.labels.db == true]     # the node that holds pgdata
      restart_policy: {condition: on-failure, max_attempts: 5, window: 120s}
      resources:
        reservations: {memory: 1G}
        limits: {memory: 2G}

networks:
  frontend:
    driver: overlay
  backend:
    driver: overlay
    driver_opts: {encrypted: "true"}

volumes:
  pgdata:

secrets:
  db_password_v1:
    external: true                                # printf %s "$PW" | docker secret create db_password_v1 -
```
