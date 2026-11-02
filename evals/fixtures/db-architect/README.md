# tidewater-tickets

Tidewater Tickets sells seats for concerts and theatre in three cities. Before the spring relaunch the
team wants the data architecture settled: what holds what, and how the pieces stay in step.

- `docs/requirements.md` — what the relaunch must do, with the numbers product has.
- `docs/current-architecture.md` — how the system works today, written by the tech lead.
- `docs/proposal-mongodb.md` — a proposal from the backend team.
- `infra/docker-compose.yml` — the services as they run today.
- `app/checkout.py`, `app/webhooks.py` — the purchase path and the payment webhook handler.
