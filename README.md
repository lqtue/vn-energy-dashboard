# Vietnam Energy Dashboard

Interactive map of Vietnam's power infrastructure — plants, transmission, substations — with filters, click-through inspection, and per-province summaries.

**Live:** https://lqtue.github.io/vn-energy-dashboard/

## Data

Open-data mockup built from:
- **Power plants** — OpenStreetMap + WRI Global Power Plant Database
- **Transmission & substations** — OpenStreetMap
- **Province boundaries** — GSO via OSM admin level 4

All layers reprojected to EPSG:4326 (WGS84). Capacity fill is sparse on plants (~10%) and wind farms are barely mapped in OSM — this build is intended as a schema and UX reference, not as authoritative asset data.

## Stack

Single-file [MapLibre GL JS](https://maplibre.org/) dashboard. No build step.

## Running locally

```
python3 -m http.server 8000
```

Then open http://localhost:8000.
