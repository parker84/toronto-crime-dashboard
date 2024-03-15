import streamlit as st
import pandas as pd
import coloredlogs, logging
from plotly import express as px
from decouple import config
logger = logging.getLogger('crime_in_your_neighbourhood')
coloredlogs.install(level=config('LOG_LEVEL', 'INFO'), logger=logger)

# TODO: check if there may be new data available and if so - trigger the make_dataset.py script to run
# TODO: have the make_dataset.py script run if crime_data.csv does not exist or if it is older than 1 day (or some other time period)

# --------------setup
st.set_page_config(
    page_title='TorCrime', 
    page_icon='🔪', 
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
        'occurence_timestamp': 'Date/Time',
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
    }
    logger.info(f"Options got got ✅. \n{options}")
    return options

@st.cache_data()
def get_df_groups(df_in):
    df_groups = {}
    for group_by in [
        ['Year'], 
        ['Crime Type', 'Year'],
        ['Offence', 'Year'],
        ['Location Type', 'Year'],
    ]:
        group = ' - '.join(group_by)
        df_groups[group] = df_in.groupby(group_by).size().reset_index()
        df_groups[group].rename(columns={0: 'Crimes'}, inplace=True)
    return df_groups

def plot_crimes_by_group(metric_df, var_to_group_by_col, metric_col='Crimes', hover_data=None):
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


# --------------load data
df = load_data(todays_date=todays_date)
options = get_options(todays_date=todays_date, df=df)


# ---------------dashboard parameters / filters
neighbourhood = st.selectbox(
    'Choose your Neighbourhood',
    ['All Neighbourhoods'] + df['Neighbourhood'].sort_values().unique().tolist(),
    index=None,
    placeholder='start typing...'
)

if neighbourhood is None:
    if st.button("Or... Find your Neighbourhood by Address 🏠"):
        st.switch_page("pages/1_🪓Crime_Near_Your_Address.py")

with st.sidebar.expander("Filtering Options", expanded=False):
    years = st.slider(
        'Year', min_value=options['min_year'], max_value=options['max_year'],
        value=(options['max_year']-5, options['max_year'])
    )
    crimes = st.multiselect(
        'Crimes',
        options=options['crime_types'],
        default=options['crime_types'],
    )

if neighbourhood is None:
    st.stop()


# --------------filtering
df_filtered = df[
    (df['Year'] >= years[0]) &
    (df['Year'] <= years[1]) &
    (df['Crime Type'].isin(crimes))
]
if neighbourhood != 'All Neighbourhoods':
    df_filtered = df_filtered[df_filtered['Neighbourhood'] == neighbourhood]
df_groups = get_df_groups(df_filtered)


# -------------plots
plot_crimes_by_group(
    metric_df=df_groups['Crime Type - Year'], 
    var_to_group_by_col='Crime Type',
    metric_col='Crimes',
)



# TODO: geo plot
# p = px.scatter_mapbox(
#     df_filtered,
#     lat='latitude',
#     lon='longitude',
#     color='Crime Type',
#     hover_name='Offence',
#     hover_data=['Location Type', 'Premises Type', 'Year', 'Month', 'Day', 'Hour', 'Day of Week', 'Neighbourhood'],
#     zoom=10,
#     height=600,
# )
# st.plotly_chart(p, use_container_width=True)



df_out = df_filtered[[
    'Date/Time', 'Crime Type', 'Offence', 'Location Type', 'Premises Type', 'Year', 'Month', 'Day', 'Hour', 'Day of Week', 'Neighbourhood'
]].sort_values(by='Date/Time', ascending=False)

st.dataframe(df_out)

# TODO: show the crimes for the neighbourhood (compare against average crimes per neighbourhood - consider confounding factors like population, etc.)

# TODO: show the crimes within the neighbourhood on a map - include hover data to see more details for each

# TODO: show the trends of crimes over each year / week / day / hour etc

# TODO: include a table to show the lower level data per crime

# TODO: then in a separate page include the ability to compare neighbourhoods