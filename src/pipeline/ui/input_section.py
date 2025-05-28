import os
import json
import streamlit as st
from pipeline.utils import Utils

def is_valid_persona_filename(filename):
    return filename.startswith("P-") and filename.endswith(".json") and filename[2:5].isdigit()

def get_existing_persona_ids():
    utils = Utils()
    sample_dir = utils.SAMPLE_PERSONA_DIR
    uploaded_dir = utils.UPLOADED_PERSONA_DIR

    ids = set()
    for folder in [sample_dir, uploaded_dir]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.endswith(".json") and is_valid_persona_filename(f):
                    ids.add(f[:-5])  # Remove ".json"
    return ids

def data_section():
    utils = Utils()
    st.subheader("🧩 Data Input")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Upload Persona Files")
        uploaded_files = st.file_uploader(
            "Upload valid P-xxx.json persona files", type="json", accept_multiple_files=True
        )

        if uploaded_files:
            existing_ids = get_existing_persona_ids()
            os.makedirs(utils.UPLOADED_PERSONA_DIR, exist_ok=True)

            for file in uploaded_files:
                filename = file.name
                if not is_valid_persona_filename(filename):
                    st.warning(f"⚠️ {filename}: Invalid filename format.")
                    continue

                persona_id = filename[:-5]
                if persona_id in existing_ids:
                    st.warning(f"⚠️ {filename}: Persona ID already exists.")
                    continue

                try:
                    content = json.load(file)
                    save_path = os.path.join(utils.UPLOADED_PERSONA_DIR, filename)
                    with open(save_path, "w", encoding="utf-8") as f:
                        json.dump(content, f, indent=2, ensure_ascii=False)
                    st.success(f"✅ Uploaded: {filename}")
                except Exception as e:
                    st.error(f"❌ Failed to save {filename}: {e}")

    with col2:
        st.markdown("### System Summary")
        try:
            system_summary = utils.load_system_summary()
            st.text_area("System Summary", system_summary, height=300)
        except Exception as e:
            st.error(f"Failed to load system summary: {e}")
