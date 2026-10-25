# Architecture

`invoicer` is a single Express process. Invoices are posted by the billing sync job and cached in SQLite
(`data/invoicer.db`, rebuilt from the sync on a cold start). HTML comes from `templates/`; PDFs are rendered by
the internal render service, authenticated with `PDF_RENDER_API_KEY`.
