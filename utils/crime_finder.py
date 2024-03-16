import streamlit as st
from utils.geocoder import GeoCoder
from geopy.distance import great_circle
import coloredlogs, logging
from tqdm import tqdm
import time
from decouple import config
logger = logging.getLogger('geo_helpers')
coloredlogs.install(level=config('LOG_LEVEL', 'INFO'), logger=logger)
geocoder = GeoCoder()

def calc_distances(filtered_crime_df, lat, lon):
    distances = []
    nrows = filtered_crime_df.shape[0]
    progress_bar = st.progress(0)
    status_text = st.empty()
    i = 1
    percentage_complete_from_last_update = 0
    for ix in tqdm(filtered_crime_df.index):
        row = filtered_crime_df.loc[ix]
        distance = great_circle((lat, lon), (row.lat, row.lon)).km
        distances.append(distance)
        percentage_complete = int(min(i / nrows, 1) * 100)
        if percentage_complete != percentage_complete_from_last_update:
            status_text.text(f"{percentage_complete}% Complete")
            progress_bar.progress(percentage_complete)
            percentage_complete_from_last_update = percentage_complete
        i += 1
    progress_bar.empty()
    return distances

@st.cache_data()
def find_crimes_near_address(address, crime_df, walking_mins=10):
    filtered_crime_df = crime_df.copy()
    logger.info("Filtering to radius around address...")
    hours = walking_mins / 60
    km_radius = round(hours * 5, 3) # we assume 5 km/h walk speed
    try:
        location = geocoder.geocode(address)
    except Exception as err:
        logger.warn(f"{err}")
        logger.warn(f"sleeping for 5 secs and trying again")
        time.sleep(5)
        location = geocoder.geocode(address)
    lat, lon = location.latitude, location.longitude
    filtered_crime_df["distance_to_address"] = calc_distances(filtered_crime_df, lat, lon)
    filtered_crime_df_within_radius = (
        filtered_crime_df
        [filtered_crime_df["distance_to_address"] <= km_radius]
    )
    logger.info("Filtered to radius around address. ✅")
    return filtered_crime_df_within_radius
