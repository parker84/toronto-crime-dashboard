import requests
import pandas as pd
import coloredlogs, logging
from datetime import datetime, timedelta
from decouple import config
logger = logging.getLogger(__name__)
coloredlogs.install(level=config('LOG_LEVEL', 'INFO'), logger=logger)

def get_yesterdays_date():
    yesterday = datetime.now() - timedelta(days=1)
    formatted_date = yesterday.strftime("%Y-%m-%d")
    return formatted_date

url = "https://services.arcgis.com/S9th0jAJ7bqgIRjw/arcgis/rest/services/Major_Crime_Indicators_Open_Data/FeatureServer/0/query"
params = {
    "where": "1=1", # get all dates
    # "where": f"Date_Field > '{get_yesterdays_date()}'", # get crimes since yesterday - no sure if this will work though bc the data only comes up to the end of 2023
    "outFields": "*",
    "outSR": 4326,
    "f": "geojson"
}
PAGE_SIZE = 2000

logger.info("Hitting the API... 🎯")

result = requests.get(url, params=params)
result_json = result.json()

offset = len(result_json['features'])
total_records = len(result_json['features'])
rows = result_json['features']
logger.info(f"total records: {total_records}, offset: {offset}... 🏃")

while result_json['properties']['exceededTransferLimit']:
    params['resultOffset'] = offset
    result = requests.get(url, params=params)
    result_json = result.json()
    if 'features' in result_json:
        rows.extend(result_json['features'])
        offset += len(result_json['features'])
        total_records += len(result_json['features'])
        logger.info(f"total records: {total_records}, offset: {offset}... 🏃")
    if len(result_json['features']) < PAGE_SIZE:
        logger.info(f"results ({len(result_json['features'])}) < PAGE_SIZE ({PAGE_SIZE}), breaking...")
        break
    if 'properties' not in result_json or 'exceededTransferLimit' not in result_json['properties']:
        logger.info(f"no more records, breaking...")
        break

logger.info(f"Creating dataframe with {total_records} records... 📊")
df = pd.DataFrame(rows)
assert df.shape[0] == total_records, f"Expected {total_records} records, got {df.shape[0]} records"
logger.info(f"Dataframe created with {df.shape[0]} records.")
logger.info(
    f"Max year/month in dataframe: {df['properties'].iloc[-1]['OCC_YEAR']}/{df['properties'].iloc[-1]['OCC_MONTH']}," +\
        f" min year/month in dataframe: {df['properties'].iloc[0]['OCC_YEAR']}/{df['properties'].iloc[0]['OCC_MONTH']} 📅")
logger.info(f"Saving data to data/crime_data.csv... 📁")
df.to_csv('data/crime_data.csv', index=True)
logger.info(f"Data saved to data/crime_data.csv ({df.shape[0]} records)")
logger.info("Done. ✅")