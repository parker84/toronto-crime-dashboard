import streamlit as st
import pandas as pd
import coloredlogs, logging
from plotly import express as px
from utils.st_helpers import (
    load_data, 
    get_options, 
    get_df_group, 
    plot_crimes_by_group, 
    sidebar_filters
)
from utils.crime_finder import find_crimes_near_address
from streamlit_theme import st_theme
from PIL import Image
from decouple import config
logger = logging.getLogger('crime_near_your_address')
coloredlogs.install(level=config('LOG_LEVEL', 'INFO'), logger=logger)

# --------------setup
cn_tower_image = Image.open('./assets/FlaviConTC.png')
st.set_page_config(
    page_title='TorCrime',
    page_icon=cn_tower_image,
    layout="wide",
    initial_sidebar_state="auto", 
    menu_items=None
)
st.title("🚔 Toronto Crime Dashboard")


# --------------load data
todays_date = pd.to_datetime('today').date()
df = load_data(todays_date=todays_date)
df['lat'] = df['Latitude']
df['lon'] = df['Longitude']
options = get_options(todays_date=todays_date, df=df)

# ---------------dashboard parameters / filters
with st.sidebar.expander("Filtering Options", expanded=False):
    years, crimes, premises = sidebar_filters(options=options)

df_filtered = df[
    (df['Year'] >= years[0]) &
    (df['Year'] <= years[1]) &
    (df['Crime Type'].isin(crimes)) &
    (df['Premises Type'].isin(premises))
]
max_year = int(df_filtered['Year'].max())

with st.form(key='my_form'):
    col1, col2 = st.columns(2)
    with col1:
        address = st.text_input(
            "Enter an address", 
            "107 Brickworks Lane, Toronto",
            help="e.g. `107 Brickworks Lane, Toronto` - no need for province or postal code"
        )
        # TODO: handle errors / weird addresses passed - ex: '107 Brickworks Lane, Toronto, ON M6N 5H8' does not work
    with col2:
        group = st.selectbox(
            'Group By',
            ['Crime Type', 'Premises Type', 'Offence', 'Location Type', 'Hour', 'Day of Week', 'Month'],
            index=0,
        )
    submit_button = st.form_submit_button(label='View Crimes 🦝', type='primary')

if submit_button:
    crimes_near_address_df = find_crimes_near_address(
        address=address, 
        crime_df=df_filtered,
        walking_mins=10
    )
    with st.spinner(f"📊 Plotting data..."):
        df_group = get_df_group(crimes_near_address_df, group_by=group)
        group_values = df_group.sort_values(by='Crimes', ascending=False)[group].unique().tolist()
        plot_crimes_by_group(
            metric_df=df_group, 
            var_to_group_by_col=group, 
            bar_chart=True,
            metric_col='Crimes', 
            hover_data=None
        )

        df_out = crimes_near_address_df[[
            'Date', 'Crime Type', 'Offence', 'Neighbourhood', 'Location Type', 'Premises Type', 'Year', 'Month', 'Day', 'Hour', 'Day of Week', 'Latitude', 'Longitude'
        ]].sort_values(by=['Date', 'Hour'], ascending=[False, True])
        df_out.index = range(1, df_out.shape[0]+1)

        st.dataframe(df_out)

    with st.spinner("Loading the map... 🗺️"):
        center = dict(lat=df_out['Latitude'].mean(), lon=df_out['Longitude'].mean())
        zoom = 13
        p = px.scatter_mapbox(
            df_out, 
            lat="Latitude", 
            lon="Longitude", 
            zoom=zoom,
            color=group,
            hover_data=[
                'Crime Type', 
                'Offence', 
                'Location Type', 
                'Premises Type', 
                'Year', 
                'Month', 
                'Day', 
                'Hour', 
                'Day of Week', 
                'Neighbourhood'
            ],
            height=800,
            width=1200,
            center=center,
        )

        theme = st_theme()
        if theme is not None:
            if theme['base'] == 'dark':
                mapbox_style="carto-darkmatter"
            else:
                mapbox_style="carto-positron"
        else:
            mapbox_style="carto-positron"

        p.update_layout(mapbox_style=mapbox_style)
        st.plotly_chart(p, use_container_width=True)

        

