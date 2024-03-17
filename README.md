# toronto-crime-dashboard
Explore Crime in Toronto by Neighbourhood.


## Running the app
```sh
virtualenv venv -p python3.11
source venv/bin/activate
pip install -r requirements.txt

export GOOGLE_API_KEY = "your-google-api-key"
streamlit run ./🔪Crime_in_Your_Neighbourhood.py
```


## Getting the Data
1. The crime data will automatically be scraped by launching the app.
2. The Toronto GeoJson / County data is already in the data folder, but if you want to see how this was obtained / cleaned you can [see that here](https://github.com/parker84/torcrime/blob/7008a45c5306d4fcbbef6c27e8d46c8adb1d987b/docs/tutorials/vizualizing_crime_data_for_toronto.md).