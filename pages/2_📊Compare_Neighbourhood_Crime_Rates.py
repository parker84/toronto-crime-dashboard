import streamlit as st
import pandas as pd
import coloredlogs, logging
from plotly import express as px
from utils.st_helpers import (
    load_data, 
    get_options, 
    plot_crimes_by_group,
    sidebar_filters,
    get_hood_140_to_nbhd_mapping,
    load_counties,
    load_neighbourhood_profiles
)
from PIL import Image
from streamlit_theme import st_theme
from decouple import config
logger = logging.getLogger('compare_neighbourhood_crime_rates')
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
st.title("📊 Toronto Crime Dashboard")

# ---------------constants
PRIMARY_METRICS = ['Total Major Crimes', 'Total Major Crimes / 1000 People', 'Total Major Crimes / km^2']

# --------------helpers
@st.cache_data()
def filter_df(df, years, crimes, premises, neighbourhoods):
    df_filtered = df[
        (df['Year'] >= years[0]) &
        (df['Year'] <= years[1]) &
        (df['Crime Type'].isin(crimes)) &
        (df['Premises Type'].isin(premises))
    ]
    if neighbourhoods != ['All Neighbourhoods 🦝']:
        df_filtered = df_filtered[df_filtered['Neighbourhood'].isin(neighbourhoods)]
    return df_filtered

@st.cache_data()
def pivot_df(df_filtered):
    max_year = int(df_filtered['Year'].max())
    df_group = df_filtered.groupby(['ID', group, 'Year']).size().reset_index()
    df_group.rename(columns={0: 'Crimes'}, inplace=True)
    df_group = df_group.merge(hood_id_map_df, on='ID', how='left')
    df_pivot = df_group.pivot(index=['ID', 'Year', 'Neighbourhood'], columns=group, values='Crimes').reset_index()
    group_vals = [col for col in df_pivot.columns if col not in ['ID', 'Year', 'Neighbourhood']]
    df_pivot['Total Major Crimes'] = df_pivot[group_vals].sum(axis=1)
    df_pivot = df_pivot.merge(nbhd_df[['ID', 'Population', 'Land Area (km^2)']], on='ID', how='left')
    df_pivot['Total Major Crimes / 1000 People'] = (df_pivot['Total Major Crimes'] / df_pivot['Population'] * 1000).round(1)
    df_pivot['Total Major Crimes / km^2'] = (df_pivot['Total Major Crimes'] / df_pivot['Land Area (km^2)']).round(1)
    df_pivot_max_year = df_pivot[df_pivot['Year'] == max_year]
    return df_pivot, df_pivot_max_year, group_vals

@st.cache_data()
def prep_data_for_viz(df_in, primary_metric):
    df_out = df_in.sort_values(by=[primary_metric], ascending=False)
    df_out = df_out[
        ["Neighbourhood", primary_metric] + 
        [col for col in PRIMARY_METRICS if col != primary_metric] +
        group_vals + 
        ["Year", "Population", "Land Area (km^2)"]
    ]
    df_out.index = range(1, len(df_out) + 1)
    df_out[primary_metric] = df_out[primary_metric].astype(float)
    for col in group_vals:
        df_out[col] = df_out[col].astype(float)
    return df_out

@st.cache_data()
def mapbox_plot(
    df_pivot_max_year, 
    counties, 
    primary_metric, 
    group_vals,
    template
):
    fig=(
        px.choropleth(df_pivot_max_year, 
            geojson=counties, 
            color=primary_metric,
            locations="ID",
            featureidkey="properties.clean_nbdh_id",
            scope="north america",
            hover_data=["Neighbourhood", primary_metric] + group_vals + ["Year"],
        )
        .update_geos(showcountries=False, showcoastlines=False, showland=False, showlakes=False, fitbounds="locations")
        .update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            template=template,
        )
    )
    st.plotly_chart(fig, use_container_width=True)

@st.cache_data()
def st_dataframe(df_out, primary_metric):
    st.dataframe(
        df_out, 
        column_config={
            "Neighbourhood": st.column_config.TextColumn(
                "Neighbourhood", width="Medium"
            ),
            primary_metric: st.column_config.ProgressColumn(
                primary_metric,
                format="%.0f",
                width="medium",
                min_value=0.0,
                max_value=df_out[primary_metric].max(),
            ),
            'Year': st.column_config.TextColumn(
                "Year", width="small"
            ),
        },
        use_container_width=True
    )

# --------------load data
todays_date = pd.to_datetime('today').date()
df = load_data(todays_date=todays_date).drop(columns=['Neighbourhood']).rename(columns={
    'neighbourhood_140': 'Neighbourhood',
    'hood_140': 'ID',
})
hood_id_map_df = get_hood_140_to_nbhd_mapping(df)
options = get_options(todays_date=todays_date, df=df)
counties = load_counties()
nbhd_df = load_neighbourhood_profiles()


# ---------------dashboard parameters / filters
col1, col2 = st.columns(2)
with col1:
    neighbourhoods = st.multiselect(
        'Choose Neighbourhoods to Compare',
        ['All Neighbourhoods 🦝'] + df['Neighbourhood'].sort_values().unique().tolist(),
        default=['All Neighbourhoods 🦝'],
        placeholder='start typing...'
    )
with col2:
    group = st.selectbox(
        'Group By',
        ['Crime Type', 'Premises Type'],
        index=0,
    )

if neighbourhoods is None:
    st.caption("If you don't know your neighbourhood, you can look it up here: [Find Your Neighbourhood](https://www.toronto.ca/city-government/data-research-maps/neighbourhoods-communities/neighbourhood-profiles/find-your-neighbourhood/#location=&lat=&lng=&zoom=)")

with st.sidebar.expander("⚙️ Advanced Options", expanded=False):
    primary_metric = st.selectbox(
        'Primary Metric',
        PRIMARY_METRICS,
        index=0,
    )
    years, crimes, premises = sidebar_filters(options=options)
st.sidebar.caption("Want to say thanks? \n[Buy me a coffee ☕](https://www.buymeacoffee.com/brydon)")

if len(neighbourhoods) == 0:
    st.stop()

# --------------filtering and transforming
df_filtered = filter_df(
    df=df, 
    years=years, 
    crimes=crimes, 
    premises=premises, 
    neighbourhoods=neighbourhoods
)
df_pivot, df_pivot_max_year, group_vals = pivot_df(df_filtered=df_filtered)
df_out = prep_data_for_viz(df_in=df_pivot_max_year, primary_metric=primary_metric)

# -------------plotting
theme = st_theme()
if theme is not None:
    if theme['base'] == 'dark':
        template = "plotly_dark"
    else:
        template = "plotly"
else:
    template = "plotly"

mapbox_plot(
    df_pivot_max_year=df_pivot_max_year, 
    counties=counties, 
    primary_metric=primary_metric, 
    group_vals=group_vals,
    template=template
)

st_dataframe(df_out=df_out, primary_metric=primary_metric)

plot_crimes_by_group(
    metric_df=df_pivot,
    var_to_group_by_col="Neighbourhood",
    metric_col=primary_metric,
    bar_chart=True,
)