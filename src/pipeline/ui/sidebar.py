import os
import streamlit as st

from pipeline.utils import Utils

def sidebar():
    st.sidebar.title("⚙️ Pipeline Configuration")
    utils = Utils()

    # SYSTEM_NAME selection from subfolders of data/
    available_systems = sorted([
        f for f in os.listdir(utils.DATA_DIR)
        if os.path.isdir(os.path.join(utils.DATA_DIR, f))
    ])
    selected_system = st.sidebar.selectbox("Select System Name", available_systems, index=available_systems.index(utils.SYSTEM_NAME))
    utils.SYSTEM_NAME = selected_system

    # LLM model selection
    model_options = ["gpt-4.1-mini", "gpt-4o-mini"]
    selected_model = st.sidebar.selectbox("Select LLM Model", model_options, index=model_options.index(utils.CURRENT_LLM))
    utils.CURRENT_LLM = selected_model

    # API key input
    st.sidebar.markdown("### 🔑 OpenAI API Key")
    api_key_input = st.sidebar.text_input("Enter your OpenAI API key", type="password")
    if api_key_input:
        if utils.save_api_key(api_key_input):
            st.sidebar.success("✅ API key saved successfully.")
        else:
            st.sidebar.error("❌ Failed to save API key.")

    st.sidebar.markdown("---")
    st.sidebar.caption("Changes will update constants in Utils.")
