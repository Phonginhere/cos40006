import sys
import os
import subprocess

import streamlit as st

def processing_log():
    st.subheader("⚙️ Run ALFRED Pipeline")

    if st.button("▶️ Execute main.py"):
        st.info("Running pipeline... please wait ⏳")
        st.code(f"📂 Current working directory (Streamlit): {os.getcwd()}")

        try:       
            ui_dir = os.path.dirname(os.path.abspath(__file__))
            pipeline_dir = os.path.dirname(ui_dir)
            src_dir = os.path.dirname(pipeline_dir)
            main_py_path = os.path.join(pipeline_dir, "main.py")
            
            # Set PYTHONPATH to include the src directory
            env = os.environ.copy()
            env["PYTHONPATH"] = src_dir
                
            process = subprocess.Popen(
                [sys.executable, main_py_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                env=env,
                errors="replace"  # replaces invalid characters with �
            )

            log_output = ""
            log_area = st.empty()

            for line in process.stdout:
                log_output += line.replace('\x00', '�')  # replace null characters if any
                log_area.text_area("📋 Real-Time Log Output", value=log_output, height=500, disabled=True)

            process.wait()
            if process.returncode == 0:
                st.success("✅ Pipeline execution completed successfully.")
            else:
                st.error(f"❌ Pipeline failed with return code {process.returncode}.")

        except Exception as e:
            st.error(f"❌ Error running pipeline: {e}")
