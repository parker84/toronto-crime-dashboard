import streamlit as st
import pandas as pd
import coloredlogs, logging
from plotly import express as px
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
st.write("Coming Soon! 🚧")