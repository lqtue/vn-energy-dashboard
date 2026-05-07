# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-file MapLibre GL dashboard for Vietnam's power infrastructure (plants, transmission, substations). The repo is a **standalone deliverable** carved out of the parent `vn_energy/` project — only the runtime artifacts live here. Source data and the scripts that produce the GeoJSON/PMTiles files in `data/` live upstream in the parent repo and are *not* part of this codebase.

Live at https://lqtue.github.io/vn-energy-dashboard/.

## Commands

There is no build step, no test suite, and no linter. The whole app is `index.html` + a service worker + static data.

- **Local dev:** `python3 -m http.server 8000` then open http://localhost:8000.
  - Local Python HTTP server returns `200 OK` to byte-range requests, which is fine for testing — but PMTiles will fall back to full-file fetches locally. To test the production range-request path, hit the deployed URL or use a server that supports ranges (e.g. `npx serve` does not; `caddy file-server` does).
- **Deploy:** `git push origin main` — GitHub Pages auto-builds from `main`/root.
- **Regenerate PMTiles** (when upstream data changes):
  ```
  tippecanoe -o data/transmission.pmtiles -Z4 -z12 -l transmission \
    --drop-densest-as-needed --extend-zooms-if-still-dropping --force \
    /path/to/upstream/transmission.geojson
  tippecanoe -o data/substations.pmtiles -Z5 -z14 -l substations -B5 \
    --drop-densest-as-needed --force /path/to/upstream/substations.geojson
  ```
- **Regenerate `data/grid_stats.json`:** `python3 ../../../scripts/processing/build_grid_stats.py` from the parent `vn_energy/` repo. The dashboard reads this for the Grid sidebar overview because PMTiles only deliver viewport tiles — aggregate counts and km totals can't be computed client-side.

## Architecture

### Data tiering — performance-critical

Cold-load is staged. Don't undo this without checking weight tradeoffs:

| Tier | What | Format | Loaded when |
|---|---|---|---|
| 1 | `plants.geojson`, `provinces.geojson`, `grid_stats.json` | GeoJSON / JSON | Blocks first paint. Total <500 KB. |
| 2 | `transmission.pmtiles` | Vector tiles | On-demand by viewport (byte-range) |
| 2 | `substations.pmtiles` | Vector tiles | On-demand by viewport |

`grid_stats.json` is a tiny pre-computed aggregate (line counts, total km by voltage band, substation counts by band). It exists because the grid layers are PMTiles, so client-side iteration is impossible — anything that would otherwise be `data.transmission.features.reduce(...)` for plants must be baked at build time for the grid.

Tier-1 files are small enough that GeoJSON is fine; switching them to PMTiles would add overhead with no benefit.

### PMTiles + jsDelivr (the non-obvious bit)

PMTiles requires HTTP `Range` requests. **GitHub Pages returns `200 OK` with the full body for ranged requests instead of `206 Partial Content`** — which breaks PMTiles. The workaround is to serve `.pmtiles` files from **jsDelivr**, which proxies GitHub raw and honors ranges:

```js
const PMT = 'https://cdn.jsdelivr.net/gh/lqtue/vn-energy-dashboard@main/data';
map.addSource('transmission', { type: 'vector', url: `pmtiles://${PMT}/transmission.pmtiles` });
```

If you migrate to a host that supports ranges (Cloudflare Pages, R2, Netlify), drop the jsDelivr indirection and use same-origin URLs.

**jsDelivr cache caveat:** the `@main` ref is cached for up to ~24h. To force a refresh after a data update, pin to a commit SHA (`@<sha>`) or bump the file path.

### Service worker (`sw.js`)

- **Cache-first, ~permanent** for `/data/*.geojson` and basemap raster tiles (CARTO, Esri).
- **Network-first** for HTML so deploys land on next visit.
- **Skips `.pmtiles`** — intercepting byte-range requests in a service worker breaks the protocol. The browser handles range caching natively.

When changing cache strategy, bump the `VERSION` constant at the top of `sw.js` to invalidate old caches.

### State and rendering

`index.html` keeps a small global `state` object (`fuels`, `capMin`, `province`, `selectedId`). All filtering is done via MapLibre filter expressions on layers (`map.setFilter('plants-circle', ...)`), not by mutating sources. Sidebar metrics are recomputed in JS by re-filtering `state.data.plants.features` — the GeoJSON is held in memory specifically for this.

Selection uses a separate `plants-selected` layer with a `==` filter on `id`, layered above `plants-circle`. Clicking the map dispatches via `map.queryRenderedFeatures()` against an explicit layer order (plants > transmission > substations), so layer Z and the click priority are coupled — keep them in sync if reordering.

### Basemap switching

Basemaps are swapped by mutating tile URLs on the existing raster sources (`map.getSource('basemap-bg').setTiles(...)`), not by reloading the style. This avoids losing the data layers. The four configurations are in the `BASEMAPS` object.

## Upstream data contract

The GeoJSON/PMTiles in `data/` are produced by `scripts/processing/build_gppd_dashboard.py` and `standardize_schema.py` in the parent `vn_energy/` repo. The standardized schema (plants: `id`, `name`, `fuel_type`, `capacity_mw`, `province`, `cod`, `status`, `owner`, `source` …) is documented there and **must not be changed unilaterally** in this repo — the dashboard relies on those exact field names in filter expressions and the click-through panel.

Fuel types in the data must match the `FUELS` array in `index.html` (Hydro, Solar, Wind, Gas, Coal, Oil, Biomass). Any new fuel needs both an SVG `<symbol>` and a `FUELS` entry, or it'll fall through to the gray "unknown" colour.
