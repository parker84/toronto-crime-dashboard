import time
import requests
import pandas as pd
import coloredlogs, logging
from decouple import config

logger = logging.getLogger(__name__)
coloredlogs.install(level=config('LOG_LEVEL', 'INFO'), logger=logger)

ARCGIS_URL = (
    "https://services.arcgis.com/S9th0jAJ7bqgIRjw/arcgis/rest/services/"
    "Major_Crime_Indicators_Open_Data/FeatureServer/0/query"
)
PAGE_SIZE = 2000
DEFAULT_OUT_PATH = 'data/cleaned_crime_data.parquet'
BASE_PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "outSR": 4326,
    "f": "geojson",
}

# Maps json_normalize columns -> the lowercase schema utils.st_helpers.load_data
# renames into Title Case. 'occurence_date' typo is preserved intentionally —
# load_data's rename map relies on it.
COLUMN_MAP = {
    'properties.CSI_CATEGORY':      'mci_category',
    'properties.OFFENCE':           'offence',
    'properties.OCC_YEAR':          'occurrence_year',
    'properties.OCC_MONTH':         'occurrence_month',
    'properties.OCC_DAY':           'occurrence_day',
    'properties.OCC_HOUR':          'occurrence_hour',
    'properties.OCC_DOW':           'occurrence_dow',
    'properties.LOCATION_TYPE':     'location_type',
    'properties.PREMISES_TYPE':     'premises_type',
    'properties.NEIGHBOURHOOD_158': 'neighbourhood_158',
    'properties.HOOD_158':          'hood_158',
    'properties.NEIGHBOURHOOD_140': 'neighbourhood_140',
    'properties.HOOD_140':          'hood_140',
}


def _get_with_retries(params, max_attempts=6):
    """ArcGIS occasionally drops the connection mid-paginate. Retry with backoff."""
    for attempt in range(1, max_attempts + 1):
        try:
            return requests.get(ARCGIS_URL, params=params, timeout=60).json()
        except (requests.ConnectionError, requests.Timeout) as err:
            if attempt == max_attempts:
                raise
            backoff = 2 ** (attempt - 1)
            logger.warning(f"request failed ({err}); retrying in {backoff}s [{attempt}/{max_attempts}]")
            time.sleep(backoff)


def _fetch_all_features():
    logger.info("Hitting the API... 🎯")
    params = dict(BASE_PARAMS)
    result = _get_with_retries(params)
    features = list(result.get('features', []))
    logger.info(f"fetched {len(features)} so far... 🏃")
    while result.get('properties', {}).get('exceededTransferLimit'):
        params['resultOffset'] = len(features)
        result = _get_with_retries(params)
        batch = result.get('features', [])
        if not batch:
            break
        features.extend(batch)
        logger.info(f"fetched {len(features)} so far... 🏃")
        if len(batch) < PAGE_SIZE:
            break
    logger.info(f"Done fetching. total features: {len(features)} ✅")
    return features


def _features_to_dataframe(features):
    logger.info("Flattening features... 🧹")
    df = pd.json_normalize(features, sep='.')
    df = df.rename(columns=COLUMN_MAP)

    # geometry.coordinates is [longitude, latitude]
    coords = df['geometry.coordinates']
    df['longitude'] = coords.str[0]
    df['latitude'] = coords.str[1]

    df['occurence_date'] = pd.to_datetime(
        df['properties.OCC_DATE'], unit='ms', errors='coerce'
    ).dt.date

    for col in ('occurrence_year', 'occurrence_day', 'occurrence_hour',
                'hood_140', 'hood_158'):
        df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
    df['occurrence_dow'] = df['occurrence_dow'].str.strip()

    keep_cols = list(COLUMN_MAP.values()) + ['occurence_date', 'latitude', 'longitude']
    df = df[keep_cols]
    logger.info(f"Flattened. shape={df.shape} ✅")
    return df


def scrape_data(write_path=DEFAULT_OUT_PATH):
    features = _fetch_all_features()
    df = _features_to_dataframe(features)
    logger.info(f"Writing parquet to {write_path}... 📁")
    df.to_parquet(write_path, index=False)
    logger.info(f"Wrote {df.shape[0]} rows to {write_path} ✅")
    return df


if __name__ == "__main__":
    scrape_data()
