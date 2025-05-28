import os
import zipfile
import shutil
import streamlit as st

from pipeline.utils import Utils

def zip_and_download(label, source_dir, zip_name):
    if not os.path.exists(source_dir) or not os.listdir(source_dir):
        st.warning(f"No data found for {label} in the path {source_dir}")
        return

    zip_path = f"{zip_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for foldername, _, filenames in os.walk(source_dir):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname=arcname)

    with open(zip_path, "rb") as f:
        st.download_button(
            label=f"📥 Download {label}",
            data=f,
            file_name=zip_name + ".zip",
            mime="application/zip"
        )

    os.remove(zip_path)

def results_section():
    st.subheader("📂 Results Explorer")

    root_results_dir = "results"
    if not os.path.exists(root_results_dir):
        st.info("No results found yet.")
        return

    systems = sorted([f for f in os.listdir(root_results_dir) if os.path.isdir(os.path.join(root_results_dir, f))])
    if not systems:
        st.info("No systems available.")
        return

    selected_system = st.selectbox("Select System", systems)
    system_path = os.path.join(root_results_dir, selected_system)

    persona_combos = sorted([f for f in os.listdir(system_path) if os.path.isdir(os.path.join(system_path, f))])
    if not persona_combos:
        st.info("No persona combinations found.")
        return

    selected_combo = st.selectbox("Select Personas Combination Abbreviation", persona_combos)
    combo_path = os.path.join(system_path, selected_combo)

    llm_models = sorted([f for f in os.listdir(combo_path) if os.path.isdir(os.path.join(combo_path, f))])
    if not llm_models:
        st.info("No LLM results found.")
        return

    selected_llm = st.selectbox("Select LLM", llm_models)
    result_root = os.path.join(combo_path, selected_llm)

    # Use updated paths from Utils
    utils = Utils()
    utils.SYSTEM_NAME = selected_system
    utils.CURRENT_LLM = selected_llm
    utils.refresh_result_paths_for_ui(selected_combo)

    st.markdown("### 📦 Download Outputs")
    col1, col2 = st.columns(2)

    with col1:
        zip_and_download("Use Cases", utils.USE_CASE_DIR, "use_cases")
        zip_and_download("Valid Use Case Tasks", utils.UNIQUE_EXTRACTED_USE_CASE_TASKS_DIR, "valid_tasks")
        zip_and_download("Valid User Stories", utils.UNIQUE_USER_STORY_DIR_PATH, "valid_user_stories")

    with col2:
        zip_and_download("Conflicts Within One Group", utils.USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, "conflicts_within")
        zip_and_download("Conflicts Across Two Groups", utils.USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR, "conflicts_across")
