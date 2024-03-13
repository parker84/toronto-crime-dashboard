import streamlit as st
import pandas as pd

# TODO: check if there may be new data available and if so - trigger the make_dataset.py script to run
# TODO: have the make_dataset.py script run if crime_data.csv does not exist or if it is older than 1 day (or some other time period)

df = pd.read_csv('data/crime_data.csv')

import ipdb; ipdb.set_trace()
neighbourhood = st.selectbox(
    'Choose your neighbourhood', 
    ('Downtown Toronto', 'East Toronto', 'West Toronto', 'Central Toronto')
)

# TODO: show the crimes for the neighbourhood (compare against average crimes per neighbourhood - consider confounding factors like population, etc.)

# TODO: show the crimes within the neighbourhood on a map - include hover data to see more details for each

# TODO: show the trends of crimes over each year / week / day / hour etc

# TODO: include a table to show the lower level data per crime

# TODO: then in a separate page include the ability to compare neighbourhoods