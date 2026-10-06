#!/usr/bin/env bash
# Build the Agent-Memory site for Netlify.
#
# Renders the mdBook in docs/book/ into website/docs using a pinned, prebuilt
# mdBook binary so the Netlify build image needs no Rust toolchain. The static
# landing page in website/ is published as-is around it.
set -euo pipefail

MDBOOK_VERSION="v0.5.3"
TARBALL="mdbook-${MDBOOK_VERSION}-x86_64-unknown-linux-gnu.tar.gz"
URL="https://github.com/rust-lang/mdBook/releases/download/${MDBOOK_VERSION}/${TARBALL}"

echo "→ Downloading mdBook ${MDBOOK_VERSION}"
curl -sSfL "$URL" -o "/tmp/${TARBALL}"
tar -xzf "/tmp/${TARBALL}" -C /tmp

echo "→ Building the book into website/docs"
/tmp/mdbook build docs/book --dest-dir "$PWD/website/docs"

echo "✓ Site ready: website/ (landing) + website/docs/ (book)"
