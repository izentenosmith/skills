#!/usr/bin/env bash
# Install the actionlint release named by ACTIONLINT_VERSION into the runner's
# PATH, refusing it unless its SHA-256 matches ACTIONLINT_SHA256. Linux x86-64.
set -euo pipefail
: "${ACTIONLINT_VERSION:?set ACTIONLINT_VERSION}" "${ACTIONLINT_SHA256:?set ACTIONLINT_SHA256}"
tarball="actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz"
dest="${RUNNER_TEMP:-$(mktemp -d)}/actionlint"
mkdir -p "$dest"
curl -fsSL -o "$dest/$tarball" \
  "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/${tarball}"
echo "${ACTIONLINT_SHA256}  $dest/$tarball" | sha256sum -c -
tar -xzf "$dest/$tarball" -C "$dest" actionlint
echo "$dest" >> "${GITHUB_PATH:-/dev/null}"
"$dest/actionlint" -version | head -1
