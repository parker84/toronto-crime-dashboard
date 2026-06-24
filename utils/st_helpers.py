import streamlit as st
import pandas as pd
import os
import requests
from utils.data_scraper import scrape_data
import coloredlogs, logging
import json
from plotly import express as px
from decouple import config
logger = logging.getLogger('crime_in_your_neighbourhood')
coloredlogs.install(level=config('LOG_LEVEL', 'INFO'), logger=logger)

# --------------constants
CLEAN_DATA_PATH = 'data/cleaned_crime_data.parquet'
RELEASE_ARTIFACT_URL = (
    "https://github.com/parker84/toronto-crime-dashboard/releases/latest/download/"
    "cleaned_crime_data.parquet"
)


def _download_release_artifact(write_path: str) -> bool:
    logger.info(f"Trying GitHub Releases artifact at {RELEASE_ARTIFACT_URL}...")
    try:
        r = requests.get(RELEASE_ARTIFACT_URL, stream=True, timeout=30)
        r.raise_for_status()
        with open(write_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
        logger.info(f"Downloaded Releases artifact to {write_path} ✅")
        return True
    except Exception as err:
        logger.warning(f"Couldn't fetch Releases artifact: {err}")
        return False


def load_or_scrape_data() -> pd.DataFrame:
    """Lazy three-tier load: local parquet → GitHub Releases → live scrape."""
    if not os.path.exists(CLEAN_DATA_PATH):
        logger.info('Local parquet missing. Trying Releases fallback...')
        if not _download_release_artifact(CLEAN_DATA_PATH):
            logger.info('Releases fallback failed. Running live scrape...')
            scrape_data(write_path=CLEAN_DATA_PATH)
    logger.info(f"Loading parquet from {CLEAN_DATA_PATH}... 📁")
    return pd.read_parquet(CLEAN_DATA_PATH)


def clean_crime_types(crime_type):
    if crime_type == 'Theft Over':
        return 'Theft Over $5k'
    else:
        return crime_type

@st.cache_data()
def load_data(todays_date):
    # todays_date - is here so that we can trigger the cache to refresh when the date changes
    df = load_or_scrape_data().rename(columns={
        'mci_category': 'Crime Type',
        'offence': 'Offence',
        'occurrence_year': 'Year',
        'occurrence_month': 'Month',
        'occurrence_day': 'Day',
        'occurrence_hour': 'Hour',
        'occurrence_dow': 'Day of Week',
        'location_type': 'Location Type',
        'premises_type': 'Premises Type',
        'neighbourhood_158': 'Neighbourhood',
        'occurence_date': 'Date',
        'latitude': 'Latitude',
        'longitude': 'Longitude',
    })
    df['Crime Type'] = df['Crime Type'].apply(clean_crime_types)
    df['Neighbourhood'] = [
        nbhd.split('(')[0].strip() for nbhd in df['Neighbourhood']
    ]
    return df

@st.cache_data()
def load_counties():
    with open("./data/Neighbourhood_Crime_Rates_Boundary_File_clean.json", "r") as f:
        counties = json.load(f)
    return counties

@st.cache_data()
def load_neighbourhood_profiles():
    neighbourhood_profiles = pd.read_csv('./data/neighbourhood-profiles-2016-140-model.csv')
    nbhd_df = pd.DataFrame([])
    nbhd_df['ID'] = pd.Series(neighbourhood_profiles[
        neighbourhood_profiles['Characteristic'] == 'Neighbourhood Number'
    ].iloc[0].values[6:]).pipe(pd.to_numeric, errors='coerce').astype('Int64')
    nbhd_df['Neighbourhood'] = neighbourhood_profiles.columns[6:]
    nbhd_df['Population'] = neighbourhood_profiles[
        neighbourhood_profiles['Characteristic'] == 'Population, 2016'
    ].iloc[0].values[6:]
    nbhd_df['Population'] = nbhd_df['Population'].str.replace(',', '').astype(int)
    nbhd_df['Land Area (km^2)'] = neighbourhood_profiles[
        neighbourhood_profiles['Characteristic'] == 'Land area in square kilometres'
    ].iloc[0].values[6:].astype(float)
    return nbhd_df

@st.cache_data()
def get_options(todays_date, df):
    # todays_date - is here so that we can trigger the cache to refresh when the date changes
    logger.info(f"Getting the options... 🎛️")
    options = {
        'crime_types': df['Crime Type'].sort_values().unique(),
        'neighbourhoods': df['Neighbourhood'].sort_values().unique(),
        'max_year': int(df['Year'].max()),
        'min_year': int(df['Year'].min()),
        'premises_types': df['Premises Type'].sort_values().unique(),
    }
    logger.info(f"Options got got ✅. \n{options}")
    return options

@st.cache_data()
def get_df_group(df_in, group_by):
    df_group = df_in.groupby([group_by, 'Year']).size().reset_index()
    df_group.rename(columns={0: 'Crimes'}, inplace=True)
    df_group = df_group.sort_values(by='Year', ascending=False)
    return df_group

@st.cache_data()
def plot_crimes_by_group(
        metric_df, 
        var_to_group_by_col, 
        bar_chart=True,
        metric_col='Crimes', 
        hover_data=None
    ):
    col1, col2 = st.columns(2)
    bar_metric_df = metric_df[metric_df[metric_col].isnull() == False]
    max_year = bar_metric_df['Year'].max()
    bar_metric_df = bar_metric_df[
        bar_metric_df['Year'] == max_year
    ]
    bar_metric_df = bar_metric_df.sort_values(by=metric_col, ascending=False)
    category_orders={
        var_to_group_by_col: bar_metric_df[var_to_group_by_col].tolist()
    }
    with col1:
        p = px.line(
                metric_df,
                x='Year',
                y=metric_col,
                color=var_to_group_by_col,
                title=f'Yearly {metric_col} by {var_to_group_by_col}',
                hover_data=hover_data,
                category_orders=category_orders
            )
        st.plotly_chart(p, use_container_width=True)
    with col2:
        if bar_chart:
            p = px.bar(
                    bar_metric_df,
                    y=var_to_group_by_col,
                    x=metric_col,
                    orientation='h',
                    title=f'{metric_col} by {var_to_group_by_col} (Year = {int(max_year)})',
                    hover_data=hover_data,
                    category_orders=category_orders
                )
        else:
            p = px.pie(
                bar_metric_df,
                names=var_to_group_by_col,
                values=metric_col,
                title=f'{metric_col} by {var_to_group_by_col} (Year = {int(max_year)})',
                hole=0.4,
                category_orders=category_orders,
                hover_data=hover_data
            )
        st.plotly_chart(p, use_container_width=True)
        return category_orders

@st.cache_data()
def show_metric(
        df, 
        y_col, 
        format_str='{:,}', 
        delta_color='normal', 
        title=None, 
        help=None, 
        calc_per_change=True
    ):
        if title is None:
            title = y_col
        if calc_per_change:
            try:
                percentage_change = (
                    100 * ((df[y_col].iloc[0] / df[y_col].iloc[1]) - 1)
                )
                delta='{change}% (YoY)'.format(
                    change=round(percentage_change, 2)
                )
            except Exception as err:
                logger.error(err)
                delta = None
        else: 
            delta = None
        st.metric(
            title,
            value=format_str.format(df[y_col].iloc[0]),
            delta=delta,
            delta_color=delta_color,
            help=help
        )

def sidebar_filters(options):
    default_max_year = int(pd.Timestamp.now().year)-1 # previous year by default
    years = st.slider(
        'Year', 
        min_value=2014, 
        max_value=options['max_year'],
        value=(options['max_year']-5, default_max_year)
    )
    crimes = st.multiselect(
        'Crimes',
        options=options['crime_types'],
        default=options['crime_types'],
    )
    premises = st.multiselect(
        'Premises',
        options=options['premises_types'],
        default=options['premises_types'],
    )
    return years, crimes, premises

def sidebar_promo():
    """Sidebar call-to-action for the real-time alerts product (torcrime.ca)."""
    st.sidebar.caption(
        "🔔 Get real-time crime alerts for your neighbourhood → "
        "[torcrime.ca](https://torcrime.ca/)"
    )

def page_footer():
    """Muted byline rendered at the bottom of each page."""
    st.divider()
    st.caption(
        "Built by [Brydon Parker](https://www.linkedin.com/in/brydon-parker/)"
    )

@st.cache_data()
def get_hood_140_to_nbhd_mapping(df):
    assert 'ID' in df.columns, 'missing "ID" column'
    assert 'Neighbourhood' in df.columns, 'missing "Neighbourhood" column'
    out_df = df[['ID', 'Neighbourhood']].drop_duplicates()
    return out_df

@st.cache_data()
def get_mapbox_plot(df, group, zoom, mapbox_style, center, category_orders=None):
    p = px.scatter_mapbox(
        df, 
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
        category_orders=category_orders
    )
    p.update_layout(mapbox_style=mapbox_style)
    return p