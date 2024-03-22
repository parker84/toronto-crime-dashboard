import streamlit as st
import pandas as pd
import coloredlogs, logging
from utils.st_helpers import (
    load_data, 
    get_options, 
    get_df_group, 
    show_metric, 
    plot_crimes_by_group, 
    sidebar_filters,
    get_mapbox_plot
)
from PIL import Image
from streamlit_theme import st_theme
from decouple import config
logger = logging.getLogger('crime_in_your_neighbourhood')
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
st.title("🦝 Toronto Crime Dashboard")

# --------------helpers
@st.cache_data()
def filter_df(df, years, crimes, premises, neighbourhood):
    df_filtered = df[
        (df['Year'] >= years[0]) &
        (df['Year'] <= years[1]) &
        (df['Crime Type'].isin(crimes)) &
        (df['Premises Type'].isin(premises))
    ]
    if neighbourhood != 'All Neighbourhoods 🦝':
        df_filtered = df_filtered[df_filtered['Neighbourhood'] == neighbourhood]    
    return df_filtered

# --------------load data
todays_date = pd.to_datetime('today').date()
df = load_data(todays_date=todays_date)
options = get_options(todays_date=todays_date, df=df)

# ---------------dashboard parameters / filters
col1, col2 = st.columns(2)
with col1:
    neighbourhood = st.selectbox(
        'Choose a Neighbourhood',
        ['All Neighbourhoods 🦝'] + df['Neighbourhood'].sort_values().unique().tolist(),
        index=None,
        placeholder='start typing...'
    )
with col2:
    group = st.selectbox(
        'Group By',
        ['Crime Type', 'Premises Type', 'Offence', 'Location Type', 'Hour', 'Day of Week', 'Month'],
        index=0,
    )

if neighbourhood is None:
    st.caption("If you don't know your neighbourhood, you can look it up here: [Find Your Neighbourhood](https://www.toronto.ca/city-government/data-research-maps/neighbourhoods-communities/neighbourhood-profiles/find-your-neighbourhood/#location=&lat=&lng=&zoom=)")

with st.sidebar.expander("⚙️ Advanced Options", expanded=False):
    years, crimes, premises = sidebar_filters(options=options)
st.sidebar.caption("Want to say thanks? \n[Buy me a coffee ☕](https://www.buymeacoffee.com/brydon)")

if neighbourhood is None:
    st.stop()

# -------------helpers
@st.cache_data()
def get_group_values(df_group, group):
    return df_group.sort_values(by='Crimes', ascending=False)[group].unique().tolist()

@st.cache_data()
def get_max_year(df_filtered):
    return int(df_filtered['Year'].max())

@st.cache_data()
def show_dataframe(df_filtered):
    df_out = df_filtered[[
        'Date', 'Crime Type', 'Offence', 'Location Type', 'Premises Type', 'Year', 'Month', 'Day', 'Hour', 'Day of Week', 'Neighbourhood', 'Latitude', 'Longitude'
    ]].sort_values(by=['Date', 'Hour'], ascending=[False, True])
    df_out.index = range(1, df_out.shape[0]+1)
    st.dataframe(df_out)
    return df_out

# --------------filtering
df_filtered = filter_df(
    df=df, 
    years=years, 
    crimes=crimes, 
    premises=premises, 
    neighbourhood=neighbourhood
)
df_group = get_df_group(df_filtered, group_by=group)
group_values = get_group_values(df_group, group)
max_year = get_max_year(df_filtered)

# -------------visuals
if group != 'Hour':
    n_group_vals = len(group_values)
    cols = st.columns(n_group_vals)
    for i in range(n_group_vals):
        group_val = group_values[i]
        with cols[i]:
            show_metric(
                df_group[
                    df_group[group] == group_val
                ],
                y_col='Crimes',
                title=group_val,
                help=f'{group_val} Crimes for `{max_year}` in {neighbourhood}',
            )

category_orders = plot_crimes_by_group(
    metric_df=df_group, 
    var_to_group_by_col=group,
    metric_col='Crimes',
    bar_chart=False,
)
 
if neighbourhood != 'All Neighbourhoods 🦝':
    df_out = show_dataframe(df_filtered)

    with st.spinner("Loading the map... 🗺️"):
        if neighbourhood == 'All Neighbourhoods 🦝':
            center = dict(lat=43.651070, lon=-79.347015)
            zoom = 11
        else:
            center = dict(lat=df_out['Latitude'].mean(), lon=df_out['Longitude'].mean())
            zoom = 13
        theme = st_theme()
        if theme is not None:
            if theme['base'] == 'dark':
                mapbox_style="carto-darkmatter"
            else:
                mapbox_style="carto-positron"
        else:
            mapbox_style="carto-positron"
        p = get_mapbox_plot(
            df=df_out, 
            group=group, 
            zoom=zoom, 
            mapbox_style=mapbox_style, 
            center=center,
            category_orders=category_orders
        )
        st.plotly_chart(p, use_container_width=True)