# toronto-crime-dashboard
Explore Crime in Toronto by Neighbourhood.

The App: https://torcrime.streamlit.app/

With the Toronto Crime Dashboard you'll be able to see:

* **🦝 Crime in Your Neighbourhood:** enter any neighbourhood in Toronto and see the Crime stats + breakdowns with interactive plots and trends over time.
* **🚔 Crime Near your Address:** view all the crimes that occurred within a 10 minute walk of your address.
* 📊 **Compare Neighbourhood Crime Rates:** see the best / worst neighbourhoods for Crime and see how yours ranks.

![image](https://github.com/parker84/toronto-crime-dashboard/assets/12496987/a1d33764-26a9-4a55-b465-0426a5bd9b1f)


## Running the app locally
```sh
virtualenv venv -p python3.11
source venv/bin/activate
pip install -r requirements.txt

export GOOGLE_API_KEY = "your-google-api-key"
streamlit run ./🦝Crime_in_Your_Neighbourhood.py
```


## Getting the Data
1. The crime data will automatically be scraped by launching the app.
2. The Toronto GeoJson / County data is already in the data folder, but if you want to see how this was obtained / cleaned you can [see that here](https://github.com/parker84/torcrime/blob/7008a45c5306d4fcbbef6c27e8d46c8adb1d987b/docs/tutorials/vizualizing_crime_data_for_toronto.md).
3. The Neighbourhood profiles data is extracted from here: https://open.toronto.ca/dataset/neighbourhood-profiles/
