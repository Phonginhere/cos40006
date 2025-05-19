import streamlit as st
import os
from pipeline.utils import Utils

def sidebar_config():
    utils = Utils()

    with st.sidebar:
        st.header("Configuration")

        # Load existing API key and sync to Utils.api_key
        def load_existing_api_key():
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                api_key_path = os.path.join(project_root, "api_key.txt")
                if os.path.exists(api_key_path):
                    with open(api_key_path, 'r') as f:
                        return f.read().strip()
                return ""
            except Exception as e:
                print(f"Error loading API key: {str(e)}")
                return ""

        existing_api_key = load_existing_api_key()
        api_key = st.text_input(
            "API Key Input",
            value=existing_api_key,
            type="password",
            help="Enter your OpenAI API key. It will be saved locally for future use."
        )

        # Update Utils.api_key if changed
        if api_key and api_key != utils.api_key:
            utils.api_key = api_key
            # Save to file for persistence
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                api_key_path = os.path.join(project_root, "api_key.txt")
                with open(api_key_path, "w") as f:
                    f.write(api_key)
            except Exception as e:
                st.error(f"Failed to save API key: {e}")
            else:
                st.success("✅ API key updated and saved.")

        if utils.api_key:
            st.info("API Key is ready to use.")
        else:
            st.warning("No API Key provided yet.")

        st.markdown("---")

        st.subheader("Model Selection")
        model_options = ["gpt-4.1-mini", "gpt-4o-mini"]

        # Use Utils.CURRENT_LLM for selection default
        selected_model = st.selectbox(
            "Select Model",
            model_options,
            index=model_options.index(utils.CURRENT_LLM) if utils.CURRENT_LLM in model_options else 0,
            help="Choose the AI model to use."
        )

        # Update Utils.CURRENT_LLM on selection change
        if selected_model != utils.CURRENT_LLM:
            utils.CURRENT_LLM = selected_model

        st.markdown("---")
        # st.caption("App by AI")
