import streamlit as st
import pandas as pd
import coloredlogs, logging
from plotly import express as px
from streamlit_theme import st_theme
from PIL import Image
from decouple import config
logger = logging.getLogger('crime_in_your_neighbourhood')
coloredlogs.install(level=config('LOG_LEVEL', 'INFO'), logger=logger)

# TODO: check if there may be new data available and if so - trigger the make_dataset.py script to run
# TODO: have the make_dataset.py script run if crime_data.csv does not exist or if it is older than 1 day (or some other time period)

# --------------setup
cn_tower_image = Image.open('./assets/FlaviConTC.png')
st.set_page_config(
    page_title='TorCrime', 
    page_icon=cn_tower_image,
    layout="wide", 
    initial_sidebar_state="auto", 
    menu_items=None
)
st.title("🔪 Toronto Crime Dashboard")


# --------------helpers
todays_date = pd.to_datetime('today').date()

@st.cache_data()
def load_data(todays_date):
    # todays_date - is here so that we can trigger the cache to refresh when the date changes
    logger.info(f"Loading the data... 📁")
    df = pd.read_csv('data/cleaned_crime_data.csv').rename(columns={
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
    logger.info(f"Data loaded. ✅ \n{df}")
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
            st.plotly_chart(p, use_container_width=True)
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

# --------------load data
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
    if st.button("Or... Find your Neighbourhood by Address 🏠"):
        st.switch_page("pages/1_🪓Crime_Near_Your_Address.py")

with st.sidebar.expander("Filtering Options", expanded=False):
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

if neighbourhood is None:
    st.stop()


# --------------filtering
df_filtered = df[
    (df['Year'] >= years[0]) &
    (df['Year'] <= years[1]) &
    (df['Crime Type'].isin(crimes)) &
    (df['Premises Type'].isin(premises))
]
if neighbourhood != 'All Neighbourhoods 🦝':
    df_filtered = df_filtered[df_filtered['Neighbourhood'] == neighbourhood]
df_group = get_df_group(df_filtered, group_by=group)
group_values = df_group.sort_values(by='Crimes', ascending=False)[group].unique().tolist()
max_year = int(df_filtered['Year'].max())


# -------------visuals
if group != 'Hour':
    top_5_group_values = group_values[:5]
    n_group_vals = len(top_5_group_values)
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

plot_crimes_by_group(
    metric_df=df_group, 
    var_to_group_by_col=group,
    metric_col='Crimes',
    bar_chart=False,
)



df_out = df_filtered[[
    'Date', 'Crime Type', 'Offence', 'Location Type', 'Premises Type', 'Year', 'Month', 'Day', 'Hour', 'Day of Week', 'Neighbourhood', 'Latitude', 'Longitude'
]].sort_values(by=['Date', 'Hour'], ascending=[False, True])
df_out.index = range(1, df_out.shape[0]+1)

st.dataframe(df_out)

with st.spinner("Loading the map... 🗺️"):
    if neighbourhood == 'All Neighbourhoods 🦝':
        center = dict(lat=43.651070, lon=-79.347015)
        zoom = 11
    else:
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
        height=600,
        width=1200,
        center=center,
    )

    theme = st_theme()
    if theme is not None:
        if theme['base'] == 'light':
            p.update_layout(mapbox_style="carto-positron")
        else:
            p.update_layout(mapbox_style="carto-darkmatter")
        st.plotly_chart(p, use_container_width=True)