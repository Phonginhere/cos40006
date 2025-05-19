import streamlit as st

from pipeline.ui.sidebar import sidebar_config
from pipeline.ui.input_section import input_section
from pipeline.ui.processing_log import processing_log
from pipeline.ui.results_section import results_section

# --- Page Configuration ---
st.set_page_config(
    page_title="Design to Streamlit App",
    layout="wide",
)

# Build UI parts
sidebar_config()
input_section()
processing_log()
results_section()
