# Agent-Memory website

The deployed site has two parts:

- **`/`** — hand-written landing page (`website/`), plain HTML + CSS, no build step.
- **`/docs/`** — the [mdBook](https://rust-lang.github.io/mdBook/) documentation, built
  from [`docs/book/`](../docs/book/) at deploy time into `website/docs/`.

```
website/
  index.html    ← landing page (content mirrors the root README)
  styles.css    ← styles
  docs/         ← GENERATED mdBook output (gitignored)
docs/book/      ← mdBook source (book.toml + src/)
netlify/build.sh← downloads pinned mdBook, renders the book into website/docs
netlify.toml    ← publish = "website", command = bash netlify/build.sh
```

## Preview locally

```sh
# build the book into website/docs (downloads a pinned mdBook binary)
bash netlify/build.sh

# serve everything
python3 -m http.server -d website 8080
# → http://localhost:8080         (landing)
# → http://localhost:8080/docs/   (book)
```

To iterate on the book alone with live reload:

```sh
mdbook serve docs/book   # → http://localhost:3000
```

## Deploy

`netlify.toml` publishes `website/` and runs `netlify/build.sh`, which downloads a
pinned mdBook binary (no Rust toolchain needed) and renders the book into
`website/docs`. Connect the repo to Netlify, or run `netlify deploy`.

## Editing

Landing-page content is hand-maintained to mirror the root `README.md`; the book
chapters live in `docs/book/src/`. When you change features, the memory model, or
benchmark claims in the README, update both to match. **Do not** add comparative
benchmark numbers that have not been measured by the harness — the site follows the same
integrity rule as the repo.
