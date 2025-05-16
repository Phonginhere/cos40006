import streamlit as st
import sys
import os
import json
import subprocess
import threading
import time
from queue import Queue
import glob
import zipfile
import io

# Add the parent directory to the path to import from src/pipeline
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Modified imports to avoid immediate API key loading
from pipeline.utils import get_llm_response, load_system_summary

# Cache
@st.cache_data
def get_cached_system_summary(system_name):
    """Cache the system summary to avoid reloading it every time"""
    try:
        return load_system_summary()
    except Exception as e:
        return f"Error loading system summary: {str(e)}"

# Function to get available model directories
@st.cache_data
def get_available_models():
    """Get available model directories from the results directory"""
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
    models = []
    try:
        if os.path.exists(results_dir):
            models = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))]
    except Exception as e:
        print(f"Error getting models: {str(e)}")
    return models

# Function to get conflict files for a specific model, group and type
def get_conflict_files(model_name, conflict_type, functional_type):
    """Get list of conflict files for a specific model, conflict type (within/cross) and functional type"""
    if not model_name:
        return []
    
    try:
        # Base path to conflicts directory for the specified model
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", model_name, "conflicts_within_one_group"
        )
        
        # Determine the directory based on functional vs non-functional
        sub_dir = "functional_user_stories" if functional_type == "functional" else "non_functional_user_stories"
        conflicts_path = os.path.join(base_path, sub_dir)
        
        if os.path.exists(conflicts_path):
            # Get all json files
            json_files = [f for f in os.listdir(conflicts_path) 
                         if f.endswith('.json')]
            return sorted(json_files)  # Return sorted list of filenames
        else:
            return []
    except Exception as e:
        print(f"Error getting conflict files: {str(e)}")
        return []

# Function to load user story data from a specific model
def load_user_story_data(model_name):
    """Load and combine user story data from all files in the selected model directory"""
    if not model_name:
        return "No model selected."
    
    try:
        # Path to the user stories directory for the specified model
        user_stories_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", model_name, "user_stories"
        )
        
        all_stories = []
        if os.path.exists(user_stories_path):
            json_files = glob.glob(os.path.join(user_stories_path, "*.json"))
            for file_path in json_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        stories = json.load(f)
                        if isinstance(stories, list):
                            all_stories.extend(stories)
                        else:
                            all_stories.append(stories)
                except Exception as e:
                    print(f"Error loading {file_path}: {str(e)}")
        
        # Convert to JSON string for download
        if all_stories:
            return json.dumps(all_stories, indent=2)
        else:
            return f"No user story data found for model: {model_name}"
    except Exception as e:
        return f"Error loading user stories: {str(e)}"

# Function to load conflict data from a specific model and type
def load_conflict_data(model_name, conflict_type, functional_type):
    """Load conflict data based on model, conflict type (within/cross) and functional type"""
    if not model_name:
        return "No model selected."
    
    try:
        # Base path to conflicts directory for the specified model
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", model_name, "conflicts_within_one_group"
        )
        
        # Determine the directory based on functional vs non-functional
        sub_dir = "functional_user_stories" if functional_type == "functional" else "non_functional_user_stories"
        conflicts_path = os.path.join(base_path, sub_dir)
        
        all_conflicts = []
        if os.path.exists(conflicts_path):
            json_files = glob.glob(os.path.join(conflicts_path, "*.json"))
            for file_path in json_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        conflicts = json.load(f)
                        if isinstance(conflicts, list):
                            all_conflicts.extend(conflicts)
                        else:
                            all_conflicts.append(conflicts)
                except Exception as e:
                    print(f"Error loading {file_path}: {str(e)}")
        
        # Convert to JSON string for download
        if all_conflicts:
            return json.dumps(all_conflicts, indent=2)
        else:
            return f"No {conflict_type} {functional_type} conflict data found for model: {model_name}"
    except Exception as e:
        return f"Error loading conflicts: {str(e)}"

def get_user_story_files(model_name):
    """Get list of user story files for a specific model"""
    if not model_name:
        return []
    
    try:
        # Path to the user stories directory for the specified model
        user_stories_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", model_name, "user_stories"
        )
        
        if os.path.exists(user_stories_path):
            # Get all json files and filter out backup files
            json_files = [f for f in os.listdir(user_stories_path) 
                         if f.endswith('.json') and not f.endswith('.bak')]
            return sorted(json_files)  # Return sorted list of filenames
        else:
            return []
    except Exception as e:
        print(f"Error getting user story files: {str(e)}")
        return []

def load_single_user_story_file(model_name, filename):
    """Load a single user story file"""
    if not model_name or not filename:
        return "No file selected."
    
    try:
        # Path to the specific user story file
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", model_name, "user_stories", filename
        )
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return f"File not found: {filename}"
    except Exception as e:
        return f"Error loading file: {str(e)}"

def load_single_conflict_file(model_name, conflict_type, functional_type, filename):
    """Load a single conflict file"""
    if not model_name or not filename:
        return "No file selected."
    
    try:
        # Base path to conflicts directory for the specified model
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", model_name, "conflicts_within_one_group"
        )
        
        # Determine the directory based on functional vs non-functional
        sub_dir = "functional_user_stories" if functional_type == "functional" else "non_functional_user_stories"
        conflicts_path = os.path.join(base_path, sub_dir)
        
        # Path to the specific conflict file
        file_path = os.path.join(conflicts_path, filename)
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return f"File not found: {filename}"
    except Exception as e:
        return f"Error loading conflict file: {str(e)}"

def load_conflict_from_custom_dir(custom_dir, filename):
    """Load a conflict file from a custom directory (for future cross-group conflicts)"""
    if not custom_dir or not filename or not os.path.exists(custom_dir):
        return "Invalid directory or filename."
    
    try:
        # Path to the specific conflict file
        file_path = os.path.join(custom_dir, filename)
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return f"File not found: {filename}"
    except Exception as e:
        return f"Error loading file: {str(e)}"

def create_user_stories_zip(model_name):
    """Create a zip file containing all user story files for a model"""
    import zipfile
    import io
    
    if not model_name:
        return None, "No model selected."
    
    try:
        # Path to the user stories directory
        user_stories_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", model_name, "user_stories"
        )
        
        if not os.path.exists(user_stories_path):
            return None, f"No user stories directory found for model: {model_name}"
        
        # Create a BytesIO object to store the zip file
        zip_buffer = io.BytesIO()
        
        # Create the zip file
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add all json files to the zip (excluding backups)
            for file_name in os.listdir(user_stories_path):
                if file_name.endswith('.json') and not file_name.endswith('.bak'):
                    file_path = os.path.join(user_stories_path, file_name)
                    zip_file.write(file_path, arcname=file_name)
        
        # Reset the buffer position to the beginning
        zip_buffer.seek(0)
        return zip_buffer, None
    except Exception as e:
        return None, f"Error creating zip file: {str(e)}"

def create_conflicts_zip(model_name, conflict_type, functional_type):
    """Create a zip file containing all conflict files for a specific model, type and functionality"""
    import zipfile
    import io
    
    if not model_name:
        return None, "No model selected."
    
    try:
        # Base path to conflicts directory for the specified model
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", model_name, "conflicts_within_one_group"
        )
        
        # Determine the directory based on functional vs non-functional
        sub_dir = "functional_user_stories" if functional_type == "functional" else "non_functional_user_stories"
        conflicts_path = os.path.join(base_path, sub_dir)
        
        if not os.path.exists(conflicts_path):
            return None, f"No {conflict_type} {functional_type} conflicts directory found for model: {model_name}"
        
        # Create a BytesIO object to store the zip file
        zip_buffer = io.BytesIO()
        
        # Create the zip file
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add all json files to the zip
            for file_name in os.listdir(conflicts_path):
                if file_name.endswith('.json'):
                    file_path = os.path.join(conflicts_path, file_name)
                    zip_file.write(file_path, arcname=file_name)
        
        # Reset the buffer position to the beginning
        zip_buffer.seek(0)
        return zip_buffer, None
    except Exception as e:
        return None, f"Error creating conflict zip file: {str(e)}"

# Initialize session state variables for process control
if 'process' not in st.session_state:
    st.session_state.process = None
if 'process_running' not in st.session_state:
    st.session_state.process_running = False
if 'output_queue' not in st.session_state:
    st.session_state.output_queue = Queue()
if 'log_content' not in st.session_state:
    st.session_state.log_content = "Waiting for processing...\n"

def save_api_key_to_file(api_key):
    """Save the API key to a temporary file for the utils functions to use"""
    try:
        # Save to project directory
        api_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "openai_api_key.txt")
        with open(api_key_path, "w") as file:
            file.write(api_key)
        return True
    except Exception as e:
        st.error(f"Error saving API key: {str(e)}")
        return False

def read_process_output(process, queue):
    """Read output from process and put it in the queue."""
    try:
        for line in iter(process.stdout.readline, b''):
            if line:
                decoded_line = line.decode('utf-8') 
                queue.put(decoded_line)
                # Print to the console for debugging
                print(f"Pipeline output: {decoded_line.strip()}")
    except Exception as e:
        queue.put(f"Error reading process output: {str(e)}\n")
    finally:
        process.stdout.close()

def run_pipeline(api_key):
    """Run the main.py pipeline in a separate process and capture its output"""
    if not save_api_key_to_file(api_key):
        st.session_state.log_content += "Failed to save API key\n"
        return False
    
    try:
        # Start the process
        pipeline_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline", "main.py")
        
        # Set working directory to the src directory to ensure relative paths work
        working_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        process = subprocess.Popen(
            [sys.executable, pipeline_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,  # Use unbuffered output for immediate feedback
            universal_newlines=False,
            cwd=working_dir
        )
        st.session_state.process = process
        st.session_state.process_running = True
        
        # Start thread to read output
        output_thread = threading.Thread(
            target=read_process_output, 
            args=(process, st.session_state.output_queue)
        )
        output_thread.daemon = True
        output_thread.start()
        
        return True
    except Exception as e:
        st.session_state.log_content += f"Error starting pipeline: {str(e)}\n"
        return False

def stop_pipeline():
    """Stop the running pipeline process"""
    if st.session_state.process is not None and st.session_state.process_running:
        try:
            st.session_state.process.terminate()
            time.sleep(0.5)
            if st.session_state.process.poll() is None:  # If process hasn't terminated
                st.session_state.process.kill()  # Force kill
            
            st.session_state.log_content += "\nProcess terminated by user.\n"
            st.session_state.process_running = False
            return True
        except Exception as e:
            st.session_state.log_content += f"\nError stopping process: {str(e)}\n"
            return False
    return False

def update_log_from_queue():
    """Update log content from the output queue"""
    if not st.session_state.output_queue.empty():
        # Collect all available lines
        lines = []
        while not st.session_state.output_queue.empty():
            line = st.session_state.output_queue.get()
            lines.append(line)
        
        # Add all lines to the log content
        for line in lines:
            st.session_state.log_content += line
        
        # Check if process has completed
        if st.session_state.process and st.session_state.process.poll() is not None:
            st.session_state.process_running = False
            exit_code = st.session_state.process.returncode
            st.session_state.log_content += f"\nProcess completed with exit code: {exit_code}\n"
        
        return True
    
    # Even if the queue is empty, check if the process has completed
    if st.session_state.process_running and st.session_state.process and st.session_state.process.poll() is not None:
        st.session_state.process_running = False
        exit_code = st.session_state.process.returncode
        st.session_state.log_content += f"\nProcess completed with exit code: {exit_code}\n"
        return True
        
    return False

def process_with_api(api_key, model_name, persona_files, system_name):
    """Process the inputs using the API based on selected model and run the main.py pipeline"""
    
    # Save API key to file for the utils functions
    if not save_api_key_to_file(api_key):
        return "Failed to save API key", False
        
    # If user uploaded persona files, save them to the appropriate directory
    if persona_files:
        try:
            # Import path from utils
            import pipeline.utils as utils
            persona_dir = utils.PERSONA_DIR
            os.makedirs(persona_dir, exist_ok=True)
            
            for file in persona_files:
                file_path = os.path.join(persona_dir, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                print(f"Saved uploaded persona file: {file.name}")
        except Exception as e:
            return f"Error saving persona files: {str(e)}", False
    
    try:
        # Import these here to avoid loading API key at module import time
        import pipeline.utils as utils
        import importlib

        # Force reload the utils module to ensure latest version is loaded
        importlib.reload(utils)

        # Now that we've saved the API key, load it
        try:
            utils.load_api_key()
        except Exception as e:
            return f"Error loading API key: {str(e)}", False
        
        # Map the UI model names to actual model identifiers
        model_mapping = {
            "Deep seek": "deepseek-coder",
            "CPT 4.0-mini": "cpt-4.0-mini",
            "GPT 4.1": "gpt-4.1-mini"
        }
        
        # Set the model in utils.py before running the pipeline
        model_id = model_mapping.get(model_name, "gpt-4o-mini")
        utils.set_current_llm(model_id)
        
        # Start the pipeline in a background process
        if run_pipeline(api_key):
            return "Pipeline started successfully", True
        else:
            return "Failed to start pipeline", False
    except Exception as e:
        return f"Error during processing: {str(e)}", False

# --- Page Configuration ---
st.set_page_config(
    page_title="Design to Streamlit App",
    layout="wide",  # Use wide layout for better use of space
)

# --- Sidebar ---
with st.sidebar:
    st.header("Configuration")

    # API Key Input - Option to choose input method
    api_key_method = st.radio("API Key Input Method", ["Text Input", "File Upload"])
    
    if api_key_method == "Text Input":
        api_key = st.text_input("API Key Input", type="password", help="Enter your API key here.")
    else:
        api_key_file = st.file_uploader("Upload API Key File", type=['txt'], help="Upload a text file containing just your API key.")
        api_key = None
        if api_key_file:
            api_key = api_key_file.getvalue().decode("utf-8").strip()
            st.success("API key loaded from file")

    # Model Selection
    model_options = ["Deep seek", "CPT 4.0-mini", "GPT 4.1"]
    selected_model = st.selectbox("Select Model", model_options, help="Choose the AI model to use.")

    st.markdown("---") # Separator
    st.caption("App by AI")


# --- Main Content Area ---
st.title("AI Processing Interface")
st.markdown("Upload your persona files, select a system summary, then view and download the results.")


# --- Input Section ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Input Persona Files (JSON)")
    persona_files = st.file_uploader("Upload Persona JSON", type=['json'], accept_multiple_files=True, label_visibility="collapsed")
    if persona_files:
        for uploaded_file in persona_files:
            st.write(f"Uploaded: {uploaded_file.name}")

with col2:
    st.subheader("Select System")
    system_summary_options = ["alfred"] # Define the options for the dropdown
    selected_system_summary = st.selectbox("Choose a system summary", system_summary_options, label_visibility="collapsed")
    if selected_system_summary:
        st.write(f"Selected: {selected_system_summary}")


# --- Result Log ---
st.subheader("Result Log")
result_log_placeholder = st.empty() # Placeholder for dynamic content

# Action buttons row
col_actions_1, col_actions_2 = st.columns([1, 3])

with col_actions_1:
    if st.button("Process Inputs", type="primary", disabled=st.session_state.process_running):
        if not api_key:
            st.warning("Please enter an API Key in the sidebar.")
        else:
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M:%S")
            st.session_state.log_content = f"Starting pipeline process at {current_time}...\n"
            st.session_state.log_content += f"Model selected: {selected_model}\n"
            st.session_state.log_content += "Initializing pipeline (this may take a minute)...\n"
            
            # Update the log immediately to show some activity
            result_log_placeholder.text_area("Log Output", st.session_state.log_content, height=400, disabled=True, key="initial_log")
            
            with st.spinner("Processing..."):
                # Call the API processing function
                result, success = process_with_api(
                    api_key=api_key,
                    model_name=selected_model,
                    persona_files=persona_files,
                    system_name=selected_system_summary
                )
                
                if not success:
                    st.session_state.log_content += f"Error: {result}\n"
                    st.error("Processing failed")

with col_actions_2:
    if st.button("Stop Process", type="secondary", disabled=not st.session_state.process_running):
        stop_pipeline()

# Auto-update the log content from the queue while the process is running
update_occurred = False
if st.session_state.process_running:
    update_occurred = update_log_from_queue()

# Display the log content
result_log_placeholder.text_area("Log Output", st.session_state.log_content, height=400, disabled=True, key="main_log")

# Use a container with auto-refresh to periodically update the log
if st.session_state.process_running:
    # Generate a random key for this refresh cycle to avoid caching
    from datetime import datetime
    refresh_key = f"refresh_{datetime.now().timestamp()}"
    
    auto_refresh = st.empty()
    with auto_refresh.container():
        st.markdown(f"Process is running... Log updates automatically. Last update: {datetime.now().strftime('%H:%M:%S')}")
        # Display spinning indicator to show activity
        with st.spinner("Processing..."):
            # This is just to show a spinner
            pass
        time.sleep(0.5)  # Reduce sleep time for more frequent updates
        st.rerun()  # Use st.rerun() for Streamlit >= 1.27.0
        
# --- Result Download Section (rest of your code remains unchanged) ---
st.markdown("---") # Separator

# --- Result Download Section ---
st.subheader("Results & Downloads")

# Get available models from the results directory
available_models = get_available_models()

# Model selection for results
if available_models:
    selected_result_model = st.selectbox(
        "Select Model for Results", 
        options=available_models,
        help="Choose which model's results to display"
    )
else:
    st.warning("No model results found in the results directory.")
    selected_result_model = None

col_results_1, col_results_2 = st.columns([1,2]) # Adjust column widths as needed

with col_results_1:
    st.markdown("##### User Stories")
    
    # Load actual user story data if a model is selected
    if selected_result_model:
        # Get list of individual user story files
        user_story_files = get_user_story_files(selected_result_model)
        
        # Combined download option
        user_stories_data = load_user_story_data(selected_result_model)
        st.download_button(
            label="All User Stories (Combined)",
            data=user_stories_data,
            file_name=f"{selected_result_model}_user_stories.json",
            mime="application/json",
        )
        
        # Zip file download option
        zip_buffer, zip_error = create_user_stories_zip(selected_result_model)
        if zip_buffer:
            st.download_button(
                label="Download All Files (ZIP)",
                data=zip_buffer,
                file_name=f"{selected_result_model}_user_stories.zip",
                mime="application/zip",
                key="zip_download"
            )
        elif zip_error:
            st.warning(zip_error)
            
        # List individual files with download options
        if user_story_files:
            st.markdown("##### Individual User Story Files")
            for file_name in user_story_files:
                file_data = load_single_user_story_file(selected_result_model, file_name)
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(file_name)
                with col2:
                    st.download_button(
                        label="Download",
                        data=file_data,
                        file_name=file_name,
                        mime="application/json",
                        key=f"download_{file_name}"
                    )
    else:
        st.info("Select a model to download user stories.")

with col_results_2:
    st.markdown("##### Conflict Analysis")

    # Within Group Conflicts
    st.markdown("###### Within Group Conflicts")
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        st.markdown("**Functional Conflicts**")
        if selected_result_model:
            # Load actual conflict data
            within_functional_data = load_conflict_data(
                selected_result_model, 
                "within", 
                "functional"
            )
            # Combined download option
            st.download_button(
                label="All Functional Conflicts (Combined)",
                data=within_functional_data,
                file_name=f"{selected_result_model}_conflict_within_functional.json",
                mime="application/json",
                key="within_functional" # Unique key for each button
            )
            
            # Zip file download option
            zip_buffer, zip_error = create_conflicts_zip(
                selected_result_model, 
                "within", 
                "functional"
            )
            if zip_buffer:
                st.download_button(
                    label="All Functional Files (ZIP)",
                    data=zip_buffer,
                    file_name=f"{selected_result_model}_conflicts_within_functional.zip",
                    mime="application/zip",
                    key="within_functional_zip"
                )
            elif zip_error:
                st.warning(zip_error)
                
            # List individual files with download options
            functional_files = get_conflict_files(selected_result_model, "within", "functional")
            if functional_files:
                st.markdown("**Individual Conflict Files:**")
                for file_name in functional_files:
                    file_data = load_single_conflict_file(
                        selected_result_model, 
                        "within", 
                        "functional", 
                        file_name
                    )
                    # Use horizontal layout without nested columns
                    st.write(f"{file_name} ", 
                             st.download_button(
                                label="Download",
                                data=file_data,
                                file_name=file_name,
                                mime="application/json",
                                key=f"download_func_{file_name}"
                             )
                    )
        else:
            st.info("Select a model to view conflicts.")
            
    with sub_col2:
        st.markdown("**Non-Functional Conflicts**")
        if selected_result_model:
            # Load actual conflict data
            within_non_functional_data = load_conflict_data(
                selected_result_model, 
                "within", 
                "non_functional"
            )
            # Combined download option
            st.download_button(
                label="All Non-Functional Conflicts (Combined)",
                data=within_non_functional_data,
                file_name=f"{selected_result_model}_conflict_within_non_functional.json",
                mime="application/json",
                key="within_non_functional"
            )
            
            # Zip file download option
            zip_buffer, zip_error = create_conflicts_zip(
                selected_result_model, 
                "within", 
                "non_functional"
            )
            if zip_buffer:
                st.download_button(
                    label="All Non-Functional Files (ZIP)",
                    data=zip_buffer,
                    file_name=f"{selected_result_model}_conflicts_within_non_functional.zip",
                    mime="application/zip",
                    key="within_non_functional_zip"
                )
            elif zip_error:
                st.warning(zip_error)
                
            # List individual files with download options
            non_functional_files = get_conflict_files(selected_result_model, "within", "non_functional")
            if non_functional_files:
                st.markdown("**Individual Conflict Files:**")
                for file_name in non_functional_files:
                    file_data = load_single_conflict_file(
                        selected_result_model, 
                        "within", 
                        "non_functional", 
                        file_name
                    )
                    # Use horizontal layout without nested columns
                    st.write(f"{file_name} ", 
                             st.download_button(
                                label="Download",
                                data=file_data,
                                file_name=file_name,
                                mime="application/json",
                                key=f"download_nonfunc_{file_name}"
                             )
                    )
        else:
            st.info("Select a model to view conflicts.")

    st.markdown("---") # Visual separator within the column

    # Cross Group Conflicts
    st.markdown("###### Cross Group Conflicts")
    
    st.markdown("**Note:** Cross-group conflicts analysis will be available in a future update.")
    
    # # Create input for future cross group conflicts directory
    # cross_group_dir = st.text_input(
    #     "Cross Group Conflicts Directory (when available)", 
    #     placeholder="Enter the path to cross group conflicts directory when available",
    #     help="This will be used in the future when cross-group conflict data is available"
    # )
    
    # if cross_group_dir and os.path.exists(cross_group_dir):
    #     st.success(f"Directory found: {cross_group_dir}")
    #     # Show files in the directory
    #     try:
    #         files = [f for f in os.listdir(cross_group_dir) if f.endswith('.json')]
    #         if files:
    #             st.write(f"Found {len(files)} JSON files in the directory")
    #             for file in files:
    #                 st.write(f"- {file}")
    #         else:
    #             st.write("No JSON files found in the directory")
    #     except Exception as e:
    #         st.error(f"Error reading directory: {str(e)}")
    # elif cross_group_dir:
    #     st.error(f"Directory not found: {cross_group_dir}")
        
    # st.info("Cross-group conflicts functionality will be implemented when the data structure is finalized.")

# --- Footer (Optional) ---
st.markdown("---")
st.caption("ALFRED User Story Analysis Interface - Results can be viewed and downloaded from different AI models.")