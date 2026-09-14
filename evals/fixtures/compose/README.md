# Shopdesk

Internal order-desk API. Flask, Postgres, RQ workers, Meilisearch for product lookup.

Run the API with `flask --app shopdesk.api run`, the worker with `rq worker`.
Schema changes live in `migrations/` and are applied by `python -m shopdesk.migrate`.
