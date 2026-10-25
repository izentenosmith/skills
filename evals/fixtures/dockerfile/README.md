# invoicer

Renders customer invoices as HTML, and as PDF through the internal render service, for the billing team.
Invoices are cached in a local SQLite database; schema changes live in `migrations/` and run at startup.

    pnpm install
    cp .env.example .env
    pnpm dev            # http://localhost:3000

## Releasing

We build and push from our laptops (the whole team is on M-series MacBooks):

    make push

then bump the image tag in `deploy/k8s/deployment.yaml` and apply it.
