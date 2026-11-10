# shopfront

Storefront API (Flask), a thumbnail worker, a one-shot migration job, Redis and Postgres, run with
`docker compose up -d` on the staging VM (`stg-1`, Ubuntu, amd64).

## Since Friday's release (v2.8.0) staging is broken

- `worker` restarts constantly. We think the new thumbnail code is crashing.
- `api` returns 500 on `/cart`. Its log says it can't connect to Redis — maybe Redis is slow to start?
  Someone suggested adding a `sleep 15` to the api's start command.
- `migrate` never completes, so the schema is behind. The entrypoint script is definitely in the image.
- `scheduler` dies with 137 too, every time it is stopped (each deploy, and when we stopped it this afternoon),
  and `docker compose up -d` hangs on it for ten seconds. Same new memory limits, presumably — give it 1g like the worker?

We captured what we could in `evidence/`. Nobody can give you access to `stg-1` this week.
