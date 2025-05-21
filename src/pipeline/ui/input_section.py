import os
import subprocess
import sys
import streamlit as st

from pipeline.utils import Utils
from pipeline.ui.utils import (
    limit_words,
    get_cached_system_summary,
    save_uploaded_persona_files,
    run_pipeline,
    stop_pipeline,
    process_with_api,
    create_zip_for_folder,
)


def input_section():
    utils = Utils()

    st.title("AI Processing Interface")
    st.markdown("Upload your persona files, select a system summary, then view and download the results.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Input Persona Files (JSON)")
        persona_files = st.file_uploader("Upload Persona JSON", type=['json'], accept_multiple_files=True, label_visibility="collapsed")
        if persona_files:
            saved_files = save_uploaded_persona_files(persona_files, utils)
            if saved_files:
                st.success(f"Saved {len(saved_files)} persona files.")

    with col2:
        st.subheader("Select System")
        # Find all subfolders in results (top level) for selection
        results_root = utils.RESULTS_DIR
        systems = [name for name in os.listdir(results_root) if os.path.isdir(os.path.join(results_root, name))]
        # Default to Utils.SYSTEM_NAME
        selected_system = st.selectbox(
            "Choose a system summary", 
            systems, 
            index=systems.index(utils.SYSTEM_NAME) if utils.SYSTEM_NAME in systems else 0,
            label_visibility="collapsed"
        )

        if selected_system:
            # Update system name in Utils singleton
            if selected_system != utils.SYSTEM_NAME:
                utils.SYSTEM_NAME = selected_system
                utils.ROOT_DATA_DIR = os.path.join("data", selected_system)
                utils.SYSTEM_SUMMARY_PATH = os.path.join(utils.ROOT_DATA_DIR, "system_summary.txt")
                utils.PERSONA_DIR = os.path.join(utils.ROOT_DATA_DIR, "personas")
                utils.UPLOADED_PERSONA_DIR = os.path.join(utils.PERSONA_DIR, "uploaded_personas")

            system_summary = utils.load_system_summary()
            st.markdown("**System Summary:**")
            st.info(system_summary)

    col_actions_1, col_actions_2 = st.columns(2)

    with col_actions_1:
        if 'process_running' not in st.session_state:
            st.session_state.process_running = False

        if st.button("Process Inputs", type="primary", disabled=st.session_state.process_running):
            api_key = utils.api_key
            model = utils.CURRENT_LLM
            system_name = utils.SYSTEM_NAME

            if not api_key:
                st.warning("Please enter your API key first.")
            elif not system_name:
                st.warning("Please select a system summary.")
            else:
                from datetime import datetime
                st.session_state.log_content = f"--- Processing started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n"
                st.session_state.log_content += f"Model selected: {model}\n"
                st.session_state.log_content += f"System selected: {system_name}\n"
                st.session_state.log_content += "Initializing pipeline (this may take a minute)...\n"

                # Save API key to src directory
                try:
                    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    api_key_path = os.path.join(src_dir, "api_key.txt")
                    
                    with open(api_key_path, "w") as f:
                        f.write(api_key)
                except Exception as e:
                    st.session_state.log_content += f"Warning: Failed to save API key: {str(e)}\n"

                with st.spinner("Processing..."):
                    try:
                        # Correctly resolve paths
                        ui_dir = os.path.dirname(os.path.abspath(__file__))
                        pipeline_dir = os.path.dirname(ui_dir)
                        src_dir = os.path.dirname(pipeline_dir)
                        main_py_path = os.path.join(pipeline_dir, "main.py")
                        
                        # Set PYTHONPATH to include the src directory
                        env = os.environ.copy()
                        env["PYTHONPATH"] = src_dir
                        
                        # Configure UTF-8 mode for Python and force UTF-8 output
                        env["PYTHONIOENCODING"] = "utf-8"
                        
                        # Create a special wrapper script to handle Unicode properly
                        wrapper_script = os.path.join(ui_dir, "run_with_ascii.py")
                        with open(wrapper_script, "w", encoding="utf-8") as f:
                            f.write("""
import sys
import os
import subprocess
import re
import time

def main():
    # Get the main script path from command line argument
    main_script = sys.argv[1]
    
    # Execute the main script and capture output
    process = subprocess.Popen(
        [sys.executable, main_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        env=os.environ,
        bufsize=1  # Line buffered
    )
    
    # Replace emojis and non-ASCII characters with ASCII equivalents
    replacements = {
        '\\U0001f4c1': '[FOLDER]',  # 📁
        '\\U0001f4be': '[SAVE]',    # 💾
        '\\U0001f50d': '[SEARCH]',  # 🔍
        '\\U00002714': '[CHECK]',   # ✔
        '\\U00002757': '[EXCLAIM]', # ❗
        '\\U0000274c': '[X]',       # ❌
        '\\U0000270b': '[HAND]',    # ✋
        '\\U0001f6ab': '[NO]',      # 🚫
        '\\U0001f389': '[PARTY]',   # 🎉
        '\\U000026a0': '[WARNING]', # ⚠
        '\\U0001f4a1': '[IDEA]',    # 💡
        '\\U0001f525': '[FIRE]',    # 🔥
        '\\U0001f440': '[EYES]',    # 👀
        '\\U0001f4dd': '[NOTE]',    # 📝
        '\\U00002705': '[CHECK]',   # ✅
    }
    
    # Process output line by line
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
            
        if line:
            # Replace emoji Unicode chars with text equivalents
            for emoji, replacement in replacements.items():
                try:
                    line = line.replace(emoji.encode('utf-8').decode('unicode_escape'), replacement)
                except:
                    pass
            
            # Remove any remaining non-ASCII characters
            line = re.sub(r'[^\\x00-\\x7F]+', '?', line)
            
            # Print the sanitized line and flush immediately
            sys.stdout.write(line)
            sys.stdout.flush()
    
    # Capture any remaining output
    remaining, _ = process.communicate()
    if remaining:
        sys.stdout.write(remaining)
        sys.stdout.flush()
        
    return process.returncode

if __name__ == "__main__":
    sys.exit(main())
""")
                        
                        # Run the process through our wrapper
                        command = [sys.executable, wrapper_script, main_py_path]
                        process = subprocess.Popen(
                            command, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.STDOUT, 
                            universal_newlines=True, 
                            cwd=src_dir,
                            env=env,
                            bufsize=1  # Line buffered
                        )
                        
                        st.session_state.process = process
                        st.session_state.process_running = True
                    except Exception as e:
                        st.session_state.log_content += f"Exception starting pipeline: {str(e)}\n"
                        st.error(f"Processing failed: {str(e)}")

    with col_actions_2:
        if st.button("Stop Process", disabled=not st.session_state.get('process_running', False)):
            if st.session_state.get('process'):
                process = st.session_state.process
                try:
                    process.terminate()
                    st.session_state.process_running = False
                    st.session_state.log_content += "Process stopped by user.\n"
                    st.rerun()
                except Exception as e:
                    st.session_state.log_content += f"Error stopping process: {str(e)}\n"

    col_actions_3, _ = st.columns([1, 3])
    with col_actions_3:
        if st.button("Clear Log"):
            st.session_state.log_content = ""
            st.rerun()