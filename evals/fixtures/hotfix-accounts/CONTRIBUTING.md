# Contributing

- Every change reaches `main` through a pull request; nobody pushes to `main` directly.
  CI (`.github/workflows/ci.yml`) must be green before merge.
- Add one line for your change under **Unreleased** in `CHANGELOG.md`. The release job
  turns that section into the next version when it tags; don't bump the version yourself.
- Production runs the latest tag. Rolling back is redeploying the previous tag.
