# cadbuildr-stdlib — showcase site

A live, browsable catalogue of the CADbuildr standard library. The entire UI is
generated from the Python catalogue manifest (`cadbuildr.stdlib.catalog`), so
**adding a part needs no changes here** — it appears automatically.

How it works: the grid is built from `public/catalog.json` (a static dump of
`get_catalog_manifest()`) and shows a pre-rendered PNG per part from
`public/thumbnails/` — so it paints instantly and uses **no WebGL contexts**.
Clicking a part opens a configurator drawer with a single live R3F viewer that
boots Pyodide, installs `cadbuildr-foundation` + the `cadbuildr-stdlib` wheel, and
renders the configured part via kernel-api (`@cadbuildr/sdk-react`).

## Regenerating thumbnails + catalog.json

Thumbnails are committed (build artifacts checked in on purpose). To refresh them
after adding/changing parts, run a kernel-api locally and use the capture page,
which renders every part in one real R3F scene and writes the PNGs:

```bash
# 1. run a local kernel-api (no auth) — e.g. from tsjs/apps/kernel-api
# 2. dump the static manifest:
python -c "import json; from cadbuildr.stdlib.catalog import get_catalog_manifest; \
  open('public/catalog.json','w').write(json.dumps(get_catalog_manifest()))"
# 3. dev server with a dummy session token + local kernel (see .env.local), then
#    open /capture.html and run  window.__captureAll()  in the console.
```

## Local dev

```bash
cd ..              # the cadbuildr-stdlib package root
uv build           # build the wheel
cd github-io
npm run sync-stdlib-wheel   # stage the wheel into public/local-stdlib/
npm install
npm run dev        # http://localhost:3009
```

Create a gitignored `.env.local` with an SDK key whose allowed origin includes
`localhost:3009`:

```
VITE_CADBUILDR_SDK_KEY_ID=<publishable keyId>
# Optional: override the project the key is scoped to (defaults to "stdlib")
# VITE_CADBUILDR_PROJECT_KEY=<project>
```

## Deploy (GitHub Pages)

`.github/workflows/deploy-pages.yml` builds the wheel, stages it, builds the Vite
site with `VITE_APP_BASE_PATH=/stdlib/`, and publishes to Pages. Set the repo
secret `CADBUILDR_SDK_KEY_ID` to a key whose allowed origin is
`https://cadbuildr.github.io` and whose allowed projects include `stdlib`.
