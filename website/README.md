# Agent-Memory website

Static landing/docs site for Agent-Memory. Plain HTML + CSS, **no build step**.

```
website/
  index.html    ← landing page (content mirrors the root README)
  styles.css    ← styles
  README.md     ← this file
netlify.toml    ← Netlify config: publish = "website", no build command
```

## Preview locally

```sh
# any static server works
python3 -m http.server -d website 8080
# → http://localhost:8080
```

## Deploy

The repo includes `netlify.toml` (publish dir `website/`, empty build command), so
connecting the repo to Netlify — or `netlify deploy --dir=website` — serves it as-is.

## Editing

Content is intentionally hand-maintained to mirror the root `README.md`. When you
change features, the memory model, or benchmark claims in the README, update
`index.html` to match. **Do not** add comparative benchmark numbers here that have
not been measured by the harness — the site follows the same integrity rule as the
repo.
