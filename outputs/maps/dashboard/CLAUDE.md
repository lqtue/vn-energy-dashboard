# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-file MapLibre GL dashboard for Vietnam's power infrastructure (plants, transmission, substations) with a target-screener + context drawer overlaid on the map. The repo is a **standalone deliverable** carved out of the parent `vn_energy/` project — only the runtime artifacts live here. Source data and the scripts that produce the GeoJSON files in `data/` live upstream in the parent repo and are *not* part of this codebase.

Live at https://lqtue.github.io/vn-energy-dashboard/.

## Commands

There is no build step, no test suite, and no linter. The whole app is `index.html` + a service worker + static GeoJSON.

- **Local dev:** `python3 -m http.server 8000` then open http://localhost:8000.
- **Deploy:** `git push origin main` — GitHub Pages auto-builds from `main`/root.
- **Regenerate data:** the four `data/*.geojson` files are produced by the parent `vn_energy/` repo (`scripts/processing/standardize_schema.py` and friends). Copy the outputs in when upstream changes.

## Architecture

### Data

All four layers are GeoJSON, loaded eagerly on map load:

| File | Used for | Size | Notes |
|---|---|---|---|
| `data/plants.geojson` | Plants layer + screener + context drawer | ~90 KB | Held in memory for screener filtering and drawer computations. |
| `data/provinces.geojson` | Province boundary outlines | ~325 KB | |
| `data/transmission.geojson` | Transmission lines | ~6.7 MB | Largest payload; blocks first paint. |
| `data/substations.geojson` | Substations | ~700 KB | |

**Tradeoff note:** an earlier build used PMTiles + a jsDelivr proxy (GitHub Pages doesn't honor HTTP `Range` requests). That was dropped in favor of plain GeoJSON for simpler handling — the cost is ~7 MB extra at cold load. If transmission grows further, the right move is either to lazy-load it on first toggle or to bring PMTiles back for that one layer.

### Sidebar layout

Top-down:

1. **Search + screener panel** — single search input (plant name filter) with a filter-toggle button that reveals an inline form (fuel pills, capacity range, COD year, status, province, owner-contains). Results list + CSV export below. Matches stay full-opacity on the map; non-matches dim. See `setupSearchScreen()` and `applyScreenHighlight()` in `index.html`.
2. **Plants card** — color-by selector (Fuel / Owner / Status / Capacity), mix bar with click-to-solo legend, capacity slider with histogram.
3. **Transmission card** — mix bar by voltage band (km totals); click a band to solo.
4. **Substations card** — voltage-band rows (count); click to solo. Layer hidden by default.
5. **Map card** — province-boundary toggle, basemap segmented control.

### Plant click → context drawer

Clicking a plant opens a slide-in drawer at the top-right of the map area (`#ctx`). Built in `openContext()` / `renderContextSections()`. Sections:

- **Asset facts** — capacity, fuel, status, COD, owner, province.
- **Grid context** — nearest substation, nearest 220 kV+ substation (transmission-grade), nearest transmission line. Distances computed in JS via haversine + point-to-segment (`pointToLineKm`).
- **Owner portfolio** (only if owner present) — count + total MW of plants by the same owner string. Listed peer rows are clickable to jump between owner assets.
- **Peers within 50 km** — grouped by fuel.
- **Province context** — rollup of all plants in the same province.

Same-owner plants get a soft accent ring on the map via the `plants-owner-highlight` layer (filter set to `==` on owner when a plant is selected).

### Color-by

The Plants card has a 4-way segmented control. State is `state.colorBy` ∈ `'fuel' | 'owner' | 'status' | 'capacity'`. Helpers in `index.html`:

- `colorExprFor(mode)` — returns the MapLibre paint expression.
- `categoryFor(feature, mode)` — string label for the feature's category.
- `colorFor(cat, mode)` — hex for a category.
- `catFilterFor(cats, mode)` — filter expression for solo'd categories.
- `orderedCatsFor(mode, byCat)` — canonical ordering for the legend.
- `buildOwnerPalette(plants)` — runs once on load; assigns colors to the top-N owners by MW; long-tail collapses to "Other", missing → "— Unknown".

Switching modes clears `state.cats` (the solo set is mode-relative).

### Map paint coordination

Two independent paint mechanisms apply to `plants-circle`:

- `circle-color` is owned by the color-by system.
- `circle-opacity` and stroke props are owned by the screener highlight (`applyScreenHighlight`).

These don't conflict because they're different paint keys, but if you add a third paint mutator be careful to keep them disjoint or coordinated.

### Service worker (`sw.js`)

- **Cache-first, ~permanent** for `/data/*.geojson` and basemap raster tiles (CARTO, Esri).
- **Network-first** for HTML so deploys land on next visit.
- Bump the `VERSION` constant when changing cache strategy or shipping a major rewrite — old clients hold on to the previous shell otherwise.

### Basemaps

Four configurations in the `BASEMAPS` object: `light`, `voyager` (streets), `dark`, `satellite`. The `light` and `dark` basemaps use CARTO's `_all` variants (labels baked in) so only the bg layer fetches tiles. Only `satellite` uses the separate labels overlay (CARTO `dark_only_labels` over Esri imagery).

CARTO tile URLs rotate across `a/b/c/d.basemaps.cartocdn.com` for parallelism. `@2x` retina tiles are not used — saves ~3× the bytes at the cost of slightly less crisp rendering on retina screens.

Switching basemaps mutates tile URLs on existing raster sources rather than reloading the style — preserves data layers.

## Upstream data contract

The GeoJSON in `data/` follows the standardized schema documented in the parent repo's CLAUDE.md. Plants must have `id`, `name`, `fuel_type`, `capacity_mw`, `province`, `cod`, `status`, `owner`, `source` — these field names are referenced directly in MapLibre filter expressions, the screener form, and the drawer rendering. **Do not change them unilaterally** in this repo.

Fuel types in the data must match the `FUELS` array in `index.html` (Hydro, Solar, Wind, Gas, Coal, Oil, Biomass — case-sensitive). Anything else falls through to the gray "unknown" colour. The owner palette is computed from the loaded data on each session.
