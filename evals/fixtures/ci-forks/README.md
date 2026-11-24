# tidepool-docs

The documentation site for the tidepool SDK: Markdown in `docs/`, rendered to static HTML in `dist/` by
`scripts/build.mjs`. No framework, Node 22.

- `npm test` checks every page builds and every internal link resolves; `npm run build` writes `dist/`.
- **CI** (`.github/workflows/ci.yml`) tests every pull request and every push to `main`, and builds the
  preview for pull requests.
- **Previews**: `.github/workflows/preview-deploy.yml` deploys each pull request's build to Cloudflare
  Pages as `pr-<number>.tidepool-docs.pages.dev` and comments the link on the pull request. Reviewers on
  the docs team read the preview, not the diff.
- **Triage** (`.github/workflows/triage.yml`) labels pull requests by the area of the docs they touch,
  and marks `WIP:` titles.
- **Production**: Cloudflare Pages builds `main` itself (Git integration); no workflow deploys it.

Secrets live in the `preview` environment: `CLOUDFLARE_API_TOKEN` (Pages: edit, on the tidepool account)
and `CLOUDFLARE_ACCOUNT_ID`.
