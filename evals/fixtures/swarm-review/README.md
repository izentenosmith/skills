# shoplane

Order and catalogue API for the shop. We go live on our own Docker Swarm cluster next week.

## Cluster

- Five Hetzner VMs: `mgr-1` and `mgr-2` are managers (two, so the cluster stays up if one fails),
  `wrk-1`..`wrk-3` are workers. Captured state in `ops/`.
- Deploys run from CI with `scripts/deploy.sh`.

## Stack (`stack.yml`)

- `edge` — nginx, terminates TLS, rate-limits each client to 10 req/s (`edge/nginx.conf`).
- `api` — waits for Postgres to be healthy before it starts (`depends_on` in the stack), three replicas.
- `worker` — background jobs.
- `postgres` — two replicas for redundancy.

Settings like the API version live in `.env` next to the stack file. The database password is a Swarm
secret (`secrets/`), so it never appears in environment variables.
