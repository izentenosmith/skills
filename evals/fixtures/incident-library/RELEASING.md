# Releasing

This is a library: there is no deployment. A release is a version on the package index.

- Publish: `scripts/publish <version>` (bumps nothing — set the version in `pyproject.toml` and `CHANGELOG.md` first, in a merged PR).
- Withdraw a broken release: `scripts/yank <version> --reason "<why>"`. Yanked versions stay installable when pinned exactly,
  but resolvers stop picking them.
- Advisories go to the repository's security/advisory page and the `#tsfmt-users` announcement channel.
- `main` is protected; changes land by pull request.
