import streamlit as st
import os
import zipfile
import io
from pipeline.utils import Utils

def results_section():
    st.subheader("Results & Downloads")

    utils = Utils()

    # Compose path to results root folder
    # 'src/results'
    base_results_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "results"))

    # Select system (all subfolders in results)
    systems = [d for d in os.listdir(base_results_dir) if os.path.isdir(os.path.join(base_results_dir, d))]
    selected_system = st.selectbox("Select System", options=systems, index=systems.index(utils.SYSTEM_NAME) if utils.SYSTEM_NAME in systems else 0)

    # Select persona abbreviation
    persona_abbr_dir = os.path.join(base_results_dir, selected_system) if selected_system else None
    personas = []
    if persona_abbr_dir and os.path.exists(persona_abbr_dir):
        personas = [d for d in os.listdir(persona_abbr_dir) if os.path.isdir(os.path.join(persona_abbr_dir, d))]
    selected_persona_abbr = st.selectbox("Select Persona Abbreviation", options=personas) if personas else None

    # Select model
    model_dir = os.path.join(persona_abbr_dir, selected_persona_abbr) if selected_persona_abbr else None
    models = []
    if model_dir and os.path.exists(model_dir):
        models = [d for d in os.listdir(model_dir) if os.path.isdir(os.path.join(model_dir, d))]
    selected_model = st.selectbox("Select Model", options=models) if models else None

    # Define a helper to create ZIP files in memory for any given folder path
    def create_zip_for_folder(folder_path):
        if not folder_path or not os.path.exists(folder_path):
            return None

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, folder_path)
                    zipf.write(full_path, rel_path)
        zip_buffer.seek(0)
        return zip_buffer

    # User Stories zip download
    if selected_system and selected_persona_abbr and selected_model:
        user_stories_path = os.path.join(base_results_dir, selected_system, selected_persona_abbr, selected_model, "user_stories")
        st.markdown("##### User Stories")
        user_stories_zip = create_zip_for_folder(user_stories_path)
        if user_stories_zip:
            st.download_button(
                "Download All User Stories (ZIP)",
                data=user_stories_zip,
                file_name=f"{selected_system}_{selected_persona_abbr}_{selected_model}_user_stories.zip",
                mime="application/zip"
            )
        else:
            st.info("No user stories found.")

        # Conflict Analysis
        st.markdown("##### Conflict Analysis")

        # Paths for conflicts
        base_conflicts_path = os.path.join(base_results_dir, selected_system, selected_persona_abbr, selected_model)

        conflicts_info = [
            ("Functional Conflicts Within Group",
             os.path.join(base_conflicts_path, "conflicts_within_one_group", "functional_user_stories"),
             f"{selected_system}_{selected_persona_abbr}_{selected_model}_conflicts_within_functional.zip"),
            ("Non-Functional Conflicts Within Group",
             os.path.join(base_conflicts_path, "conflicts_within_one_group", "non_functional_user_stories"),
             f"{selected_system}_{selected_persona_abbr}_{selected_model}_conflicts_within_non_functional.zip"),
            ("Functional Conflicts Across Groups",
             os.path.join(base_conflicts_path, "conflicts_across_two_groups", "functional_user_stories"),
             f"{selected_system}_{selected_persona_abbr}_{selected_model}_conflicts_across_functional.zip"),
            ("Non-Functional Conflicts Across Groups",
             os.path.join(base_conflicts_path, "conflicts_across_two_groups", "non_functional_user_stories"),
             f"{selected_system}_{selected_persona_abbr}_{selected_model}_conflicts_across_non_functional.zip"),
        ]

        for label, folder_path, zip_name in conflicts_info:
            zip_data = create_zip_for_folder(folder_path)
            if zip_data:
                st.download_button(
                    label,
                    data=zip_data,
                    file_name=zip_name,
                    mime="application/zip"
                )
            else:
                st.info(f"No {label.lower()} found.")
