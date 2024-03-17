import streamlit as st
import pandas as pd
import json
import coloredlogs, logging
from plotly import express as px
from utils.st_helpers import (
    load_data, 
    get_options, 
    plot_crimes_by_group,
    sidebar_filters,
    get_hood_140_to_nbhd_mapping
)
from PIL import Image
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

# --------------load data
todays_date = pd.to_datetime('today').date()
df = load_data(todays_date=todays_date).drop(columns=['Neighbourhood']).rename(columns={
    'neighbourhood_140': 'Neighbourhood',
    'hood_140': 'ID',
})
df['Neighbourhood'] = [
    nbhd.split('(')[0].strip() for nbhd in df['Neighbourhood']
]
hood_id_map_df = get_hood_140_to_nbhd_mapping(df)
options = get_options(todays_date=todays_date, df=df)
with open("./data/Neighbourhood_Crime_Rates_Boundary_File_clean.json", "r") as f:
    counties = json.load(f)

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

with st.sidebar.expander("Filtering Options", expanded=False):
    years, crimes, premises = sidebar_filters(options=options)

if len(neighbourhoods) == 0:
    st.stop()

# --------------filtering
df_filtered = df[
    (df['Year'] >= years[0]) &
    (df['Year'] <= years[1]) &
    (df['Crime Type'].isin(crimes)) &
    (df['Premises Type'].isin(premises))
]
max_year = int(df_filtered['Year'].max())
if neighbourhoods != ['All Neighbourhoods 🦝']:
    df_filtered = df_filtered[df_filtered['Neighbourhood'].isin(neighbourhoods)]
df_group = df_filtered.groupby(['ID', group, 'Year']).size().reset_index()
df_group.rename(columns={0: 'Crimes'}, inplace=True)
df_group = df_group.merge(hood_id_map_df, on='ID', how='left')
df_pivot = df_group.pivot(index=['ID', 'Year', 'Neighbourhood'], columns=group, values='Crimes').reset_index()
group_vals = [col for col in df_pivot.columns if col not in ['ID', 'Year', 'Neighbourhood']]
df_pivot['Total Major Crimes'] = df_pivot[group_vals].sum(axis=1)
df_pivot_max_year = df_pivot[df_pivot['Year'] == max_year]

fig=(
    px.choropleth(df_pivot_max_year, 
        geojson=counties, 
        color="Total Major Crimes",
        locations="ID",
        featureidkey="properties.clean_nbdh_id",
        color_continuous_scale="Viridis",
        scope="north america",
        hover_data=["Neighbourhood", "Total Major Crimes"] + group_vals + ["Year"],
    )
    .update_geos(showcountries=False, showcoastlines=False, showland=False, showlakes=False, fitbounds="locations")
    .update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
    )
)
st.plotly_chart(fig, use_container_width=True)

df_out = df_pivot_max_year.sort_values(by=["Total Major Crimes"], ascending=False)
df_out = df_out[["Neighbourhood", "Total Major Crimes"] + group_vals + ["Year"]]
df_out.index = range(1, len(df_out) + 1)
df_out['Total Major Crimes'] = df_out['Total Major Crimes'].astype(float)
for col in group_vals:
    df_out[col] = df_out[col].astype(float)
st.dataframe(
    df_out, 
    column_config={
        "Neighbourhood": st.column_config.TextColumn(
            "Neighbourhood", width="Medium"
        ),
        'Total Major Crimes': st.column_config.ProgressColumn(
            "Total Major Crimes",
            format="%.0f",
            width="medium",
            min_value=0.0,
            max_value=df_out['Total Major Crimes'].max(),
        ),
        'Year': st.column_config.TextColumn(
            "Year", width="small"
        ),
    },
    use_container_width=True
)


plot_crimes_by_group(
    metric_df=df_pivot,
    var_to_group_by_col="Neighbourhood",
    metric_col="Total Major Crimes",
    bar_chart=True,
)