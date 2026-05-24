# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```sh
virtualenv venv -p python3.11
source venv/bin/activate
pip install -r requirements.txt

# GOOGLE_API_KEY is required for the geocoder fallback used by the
# "Crime Near Your Address" page. Read from .env via python-decouple.
export GOOGLE_API_KEY="your-google-api-key"

streamlit run ./🦝Crime_in_Your_Neighbourhood.py
```

There is no test suite, linter, or build step — Streamlit hot-reloads the entry script on save. `LOG_LEVEL` (default `INFO`) is also read via `decouple.config` and controls `coloredlogs` output for every module.

## Architecture

This is a multi-page Streamlit app over Toronto Major Crime Indicator (MCI) open data. The three pages share data loading + filtering helpers in `utils/st_helpers.py`, and Streamlit's filename-based router stitches them together:

- `🦝Crime_in_Your_Neighbourhood.py` — top-level entry; per-neighbourhood breakdown.
- `pages/1_🚔Crime_Near_Your_Address.py` — geocodes an address and filters to a walking-radius (5 km/h × `walking_mins`).
- `pages/2_📊Compare_Neighbourhood_Crime_Rates.py` — choropleth + ranked table across neighbourhoods, joining crime counts to 2016 Neighbourhood Profile population/area.

### Data pipeline (lazy, three-tier)

`utils/st_helpers.load_or_scrape_data` resolves `data/cleaned_crime_data.parquet` in three tiers:

1. Local parquet exists on disk → load it.
2. Else fetch `https://github.com/parker84/toronto-crime-dashboard/releases/latest/download/cleaned_crime_data.parquet` (published daily by `.github/workflows/scrape-crime-data.yml`) and load it.
3. Else live-scrape via `utils/data_scraper.scrape_data` — paginates the ArcGIS `Major_Crime_Indicators_Open_Data` FeatureServer (`PAGE_SIZE=2000`, follows `exceededTransferLimit`), flattens features with `pd.json_normalize`, projects to the lowercase schema `load_data` expects, and writes parquet.

There is no intermediate raw CSV anymore; the scraper produces the cleaned parquet in one pass. Force a refresh by deleting `data/cleaned_crime_data.parquet` (next launch hits tier 2 or 3) or by running `python -m utils.data_scraper` directly. The cron workflow re-runs the scrape at 06:00 UTC daily and uploads a fresh Release artifact (`data-YYYY-MM-DD` tag, `latest` always points to newest).

### Column renaming convention

The scraper emits lowercase columns (`mci_category`, `occurrence_year`, `neighbourhood_158`, `latitude`, …) and `load_data` renames them to Title Case (`Crime Type`, `Year`, `Neighbourhood`, `Latitude`, …). Downstream pages and helpers reference only the renamed columns. The neighbourhood-comparison page additionally renames `neighbourhood_140` → `Neighbourhood` and `hood_140` → `ID` because the 2016 Neighbourhood Profiles dataset is keyed on the 140-neighbourhood scheme, not the current 158.

Note the typo `occurence_date` (one `r`) is preserved end-to-end — the scraper emits it that way and `load_data`'s rename map relies on it. Don't "fix" the spelling without updating both ends in lockstep. The source field `CSI_CATEGORY` is mapped to `mci_category` at scrape time (the upstream rename from `MCI_CATEGORY` → `CSI_CATEGORY` happened in early 2026; downstream code still uses the historical name).

### Neighbourhood ID join

Three datasets have to align on neighbourhood ID for page 2's choropleth to work:

- Crime data (`hood_140`, `hood_158`) — emitted as `Int64` by the scraper.
- `data/Neighbourhood_Crime_Rates_Boundary_File_clean.json` — `properties.clean_nbdh_id` is native `int`.
- `data/neighbourhood-profiles-2016-140-model.csv` — IDs are strings like `"20"`/`"129"` in the raw file; `load_neighbourhood_profiles` coerces them to `Int64` so the merge works.

The ArcGIS API serves these as zero-padded strings (`"001"`), so without coercion the join silently drops most rows. If you change the scraper output dtype, update `load_neighbourhood_profiles` in lockstep.

### Caching

Nearly every helper that reads, filters, or plots data is wrapped in `@st.cache_data()`. `load_data` and `get_options` take a `todays_date` argument purely as a cache key so the cache rolls over once a day. When editing these helpers, preserve the cache decorator and remember that mutating inputs in-place will corrupt cached results across reruns.

### Geocoding (`utils/geocoder.py`)

`GeoCoder.geocode` tries Nominatim first, retries with `_clean_address` (strips suffixes like `st`/`ave`/`n`, appends `, Canada`), and only falls back to Google Maps (`GOOGLE_API_KEY`) when the cleaned address still misses *and* the original looked like a real street address. The Google fallback is gated this way because Google returns a result for almost any string, which masks geocoding errors.

### Theming

Pages call `streamlit_theme.st_theme()` at render time and branch on `theme['base']` to pick `carto-darkmatter` vs `carto-positron` Mapbox tiles (or `plotly_dark` vs `plotly` for choropleths). `st_theme()` returns `None` on first render — always guard with `if theme is not None`.

## Conventions worth preserving

- The repo intentionally uses emoji in filenames (`🦝Crime_in_Your_Neighbourhood.py`, `pages/1_🚔…py`) — Streamlit renders these as the sidebar nav labels. Don't rename without a reason.
- Sidebar filters live in `sidebar_filters(options)` and are reused across all three pages — change them there, not per-page.
- The `'All Neighbourhoods 🦝'` sentinel string (with trailing raccoon) is the "no filter" marker on pages 1 and 3; matching is exact-string, so keep it in sync if you ever rename it.
