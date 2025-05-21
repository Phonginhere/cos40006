import streamlit as st
import time
from datetime import datetime
import select
import io

def processing_log():
    st.subheader("Processing Log")

    if 'log_content' not in st.session_state:
        st.session_state.log_content = ""

    if 'process_running' not in st.session_state:
        st.session_state.process_running = False

    if 'auto_scroll' not in st.session_state:
        st.session_state.auto_scroll = True

    process = st.session_state.get('process', None)

    # Read stdout from subprocess and append to log_content
    if process and st.session_state.process_running:
        try:
            # Use a non-blocking approach to read available output
            output = ""
            
            # Poll to check if there's data to read
            if process.stdout:
                # Read as much as possible without blocking
                while True:
                    line = process.stdout.readline()
                    if line:
                        output += line
                    else:
                        break
                
                if output:
                    st.session_state.log_content += output
            
            # Check if process ended
            if process.poll() is not None:
                # Get any remaining output
                remaining_output, _ = process.communicate(timeout=0.5)
                if remaining_output:
                    st.session_state.log_content += remaining_output
                
                st.session_state.process_running = False
                st.session_state.log_content += f"\nProcess exited with code {process.returncode}\n"
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            st.session_state.log_content += f"\nError reading process output: {e}\n{error_details}\n"

    col_scroll1, col_scroll2 = st.columns([1, 3])
    with col_scroll1:
        scroll_label = "Disable Auto-Scroll" if st.session_state.auto_scroll else "Enable Auto-Scroll"
        if st.button(scroll_label, key="toggle_auto_scroll"):
            st.session_state.auto_scroll = not st.session_state.auto_scroll
            st.rerun()

    with col_scroll2:
        scroll_status = "📜 Auto-scrolling enabled (follows new logs)" if st.session_state.auto_scroll else "🔒 Auto-scrolling disabled (view stays in place)"
        st.info(scroll_status)

    if st.session_state.log_content:
        log_content = st.session_state.log_content
        num_lines = log_content.count('\n') + 1
        height = min(max(400, num_lines * 20), 600)

        if st.session_state.auto_scroll:
            key = f"refresh_{datetime.now().timestamp()}"
        else:
            key = "fixed_log_key"
        
        st.text_area("Log Output", log_content, height=height, disabled=True, key=key)

    if st.session_state.process_running:
        with st.spinner("Processing..."):
            time.sleep(0.5)
            st.rerun()