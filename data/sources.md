# Data Sources Registry

Track every dataset added to `data/raw/`. One entry per source dataset.

---

## Datasets

### EVN Hydropower Reservoir Levels (Daily/Hourly)
- **topic:** power_infrastructure, water_management
- **provider:** Electricity Vietnam (EVN)
- **url_or_path:** https://hochuathuydien.evn.com.vn/PageHoChuaThuyDienEmbedEVN.aspx
- **date_acquired:** 2026-05-08
- **format:** Time-series (Scraped HTML to CSV)
- **crs:** N/A
- **license:** Public EVN Data
- **coverage:** Major hydropower reservoirs across Vietnam
- **description:** Real-time and historical water levels, inflow, and discharge rates.
- **processing_script:** scripts/ingestion/evn_hydro.py
- **status:** active (automated via GitHub Actions)
- **notes:** Data is scraped hourly.
