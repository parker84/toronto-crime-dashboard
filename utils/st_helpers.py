import streamlit as st
import pandas as pd
import os
from utils.data_cleaner import clean_data
from utils.data_scraper import scrape_data
import coloredlogs, logging
from plotly import express as px
from decouple import config
logger = logging.getLogger('crime_in_your_neighbourhood')
coloredlogs.install(level=config('LOG_LEVEL', 'INFO'), logger=logger)

# --------------constants
RAW_DATA_PATH = 'data/crime_data.csv'
CLEAN_DATA_PATH = 'data/cleaned_crime_data.csv'


def load_or_scrape_data() -> pd.DataFrame:
    """Loads the data if it exists, otherwise scrapes and cleans the data and then returns it.

    Returns:
        pd.DataFrame: clean data
    """
    logger.info('Checking if cleaned data exists...')
    if os.path.exists(CLEAN_DATA_PATH):
        logger.info('Clean data exists.')
        logger.info(f"Loading the data... 📁")
        df = pd.read_csv(CLEAN_DATA_PATH)
        logger.info(f"Data loaded. ✅ \n{df}")
    else:
        logger.info('Cleaned data does not exist...')
        if not os.path.exists(RAW_DATA_PATH):
            logger.info('Raw data does not exist...')
            scrape_data(write_path=RAW_DATA_PATH)
        df = pd.read_csv(RAW_DATA_PATH)
        clean_data(in_df=df, save_path=CLEAN_DATA_PATH)
    return df

def check_if_data_is_up_to_date(df) -> bool:
    return True # TODO: implement this

def update_data(df) -> pd.DataFrame:
    pass # TODO: implement this

@st.cache_data()
def load_data(todays_date):
    # todays_date - is here so that we can trigger the cache to refresh when the date changes
    df = load_or_scrape_data()
    data_is_up_to_date = check_if_data_is_up_to_date(df)
    if not data_is_up_to_date:
        df = update_data(df)
    df = pd.read_csv(CLEAN_DATA_PATH).rename(columns={
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
    return df

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
    years = st.slider(
        'Year', min_value=2014, max_value=options['max_year'],
        value=(options['max_year']-5, options['max_year'])
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
