# invoicer

Invoicing for our customers: a Flask API, a background worker that renders invoice PDFs and
thumbnails, and Postgres. A separate `reports` service runs on the company Kubernetes cluster.

## Production

- **invoicer** runs on one VM (`inv-prod-1`, Ubuntu 24.04) with Docker Engine. `scripts/deploy.sh`
  pulls and restarts the stack from `docker-compose.prod.yml`.
- The VM's firewall (`ufw`) allows only 22, 80 and 443 from the internet, so the Postgres port is not
  reachable from outside. We publish 5432 so the on-call engineer can connect with a GUI over SSH.
- `updater` keeps images current automatically; it only has read-only access to Docker.
- `worker` needs the VM's GPU (`/dev/dri`) for thumbnail rendering.
- **reports** runs on the shared `platform` cluster (`k8s/reports.yaml`), exposed through the
  cluster's ingress at `reports.invoicer.example.com`.

Secrets live in `.env` on the VM (see `.env.example`).
