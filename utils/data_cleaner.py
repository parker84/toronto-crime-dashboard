import pandas as pd
import coloredlogs, logging
from decouple import config
from datetime import datetime
from tqdm import tqdm
logger = logging.getLogger(__name__)
coloredlogs.install(level=config('LOG_LEVEL', 'INFO'), logger=logger)


def clean_data(in_df: pd.DataFrame, save_path: str):
    df = in_df.copy()
    logger.info("Cleaning the data... 🧹")

    new_cols = []
    # Create a progress bar using tqdm
    n_rows = df.shape[0]
    for i in tqdm(range(n_rows)):
        row = df.iloc[i] # => we just need to ensure we keep the order correct
        new_row = {}
        #-----------geometry
        new_row['latitude'] = eval(row['geometry'])['coordinates'][1]
        new_row['longitude'] = eval(row['geometry'])['coordinates'][0]
        #-----------properties
        # location
        new_row['premises_type'] = eval(row['properties'])['PREMISES_TYPE']
        new_row['location_type'] = eval(row['properties'])['LOCATION_TYPE']
        # dates
        new_row['occurrence_year'] = eval(row['properties'])['OCC_YEAR']
        new_row['occurrence_month'] = eval(row['properties'])['OCC_MONTH']
        new_row['occurrence_day'] = eval(row['properties'])['OCC_DAY']
        new_row['occurrence_hour'] = eval(row['properties'])['OCC_HOUR']
        new_row['occurrence_dow'] = eval(row['properties'])['OCC_DOW']
        new_row['occurence_timestamp'] = datetime.fromtimestamp(eval(row['properties'])['OCC_DATE'] / 1000) # / 1k bc ms to s
        new_row['occurence_date'] = new_row['occurence_timestamp'].date()
        # type of crime
        new_row['offence'] = eval(row['properties'])['OFFENCE']
        new_row['mci_category'] = eval(row['properties'])['MCI_CATEGORY']
        # neighbourhood
        new_row['neighbourhood_158'] = eval(row['properties'])['NEIGHBOURHOOD_158']
        new_row['hood_158'.lower()] = eval(row['properties'])['HOOD_158']
        new_row['neighbourhood_140'] = eval(row['properties'])['NEIGHBOURHOOD_140']
        new_row['hood_140'.lower()] = eval(row['properties'])['HOOD_140']
        new_cols.append(new_row)
        if i % 10000 == 0:
            logger.info(f"Cleaned {i+1}/{n_rows} rows ... 🏃")

    new_df = pd.DataFrame(new_cols)
    df.reset_index(drop=True, inplace=True)
    new_df.reset_index(drop=True, inplace=True)
    assert df.shape[0] == new_df.shape[0], f"Expected {df.shape[0]} records, got {new_df.shape[0]} records"
    df = df.join(new_df)
    logger.info(f"Data cleaned. ✅ \n{df}")
    assert in_df.shape[0] == df.shape[0], f"Expected {in_df.shape[0]} output records, got {df.shape[0]} output records"
    logger.info(f"Saving data to {save_path}... 📁")
    df.to_csv(save_path, index=False)
    logger.info("Data saved. ✅")
    logger.info("Done. 🎉")
    return df

if __name__ == "__main__":
    df = pd.read_csv('data/crime_data.csv')
    df = df.drop(columns=['Unnamed: 0'])
    clean_df = clean_data(df, save_path='data/cleaned_crime_data.csv')
    