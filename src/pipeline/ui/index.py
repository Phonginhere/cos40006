import streamlit as st

from pipeline.ui.sidebar import sidebar
from pipeline.ui.input_section import data_section
from pipeline.ui.processing_log import processing_log
from pipeline.ui.results_section import results_section

# Set up page configuration
st.set_page_config(
    page_title="System Requirement Generation Pipeline",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Render sidebar configuration
sidebar()

# Title and Sections
st.title("System Automated Requirements Generation Pipeline")

# Section 1: Input
with st.expander("1️⃣ Input & System Overview", expanded=True):
    data_section()

# Section 2: Processing
with st.expander("2️⃣ Pipeline Execution Log", expanded=True):
    processing_log()

# Section 3: Results
with st.expander("3️⃣ Results & Downloads", expanded=True):
    results_section()
