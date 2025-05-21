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

# Don't import functions that require API key yet - we'll import them when needed
# The pipeline.utils module will be imported only when explicitly needed

# Cache
@st.cache_data
def get_cached_system_summary(system_name):
    """Cache the system summary to avoid reloading it every time"""
    try:
        # Directly read the system summary from the data file
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        summary_path = os.path.join(project_root, "data", system_name, "system_summary.txt")
        
        if os.path.exists(summary_path):
            with open(summary_path, 'r') as f:
                return f.read().strip()
        else:
            # Provide a fallback summary if the file doesn't exist
            if system_name == "alfred":
                return "Seems like we do not have alfred summary yet."
            return f"System summary not found for {system_name}."
    except Exception as e:
        return f"Error loading system summary: {str(e)}"

# Function to get available persona combinations
@st.cache_data
def get_available_systems():
    """Get available system directories from the results directory"""
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
    systems = []
    try:
        if os.path.exists(results_dir):
            systems = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))]
    except Exception as e:
        print(f"Error getting available systems: {str(e)}")
    return systems

@st.cache_data
def get_available_persona_combinations(system_name):
    """Get available persona combination directories for a specific system"""
    if not system_name:
        return []
        
    system_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", system_name)
    persona_combinations = []
    try:
        if os.path.exists(system_path):
            persona_combinations = [d for d in os.listdir(system_path) if os.path.isdir(os.path.join(system_path, d))]
    except Exception as e:
        print(f"Error getting persona combinations for {system_name}: {str(e)}")
    return persona_combinations

# Function to get models for a specific persona combination
@st.cache_data(ttl=60)
def get_models_for_persona(system_name, persona_combination):
    """Get available model directories for a specific system and persona combination"""
    if not system_name or not persona_combination:
        return []
        
    persona_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", system_name, persona_combination)
    models = []
    try:
        if os.path.exists(persona_path):
            models = [d for d in os.listdir(persona_path) if os.path.isdir(os.path.join(persona_path, d))]
    except Exception as e:
        print(f"Error getting models for {system_name}/{persona_combination}: {str(e)}")
    return models

# For backwards compatibility
@st.cache_data
def get_available_models():
    """Get all available model directories from all persona combinations (flat list)"""
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
    all_models = []
    try:
        if os.path.exists(results_dir):
            persona_dirs = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))]
            for persona_dir in persona_dirs:
                persona_path = os.path.join(results_dir, persona_dir)
                models = [os.path.join(persona_dir, m) for m in os.listdir(persona_path) 
                         if os.path.isdir(os.path.join(persona_path, m))]
                all_models.extend(models)
    except Exception as e:
        print(f"Error getting all models: {str(e)}")
    return all_models

# Function to get conflict files for a specific model, group and type
def get_conflict_files(system_name, persona_combination, model_name, conflict_type, functional_type, validity_type="valid"):
    """Get list of conflict files for a specific model, conflict type (within/cross), functional type and validity type
    
    Parameters:
    -----------
    system_name : str
        The system name (e.g., 'alfred')
    persona_combination : str
        The persona combination folder name
    model_name : str
        The model name (e.g., 'gpt-4.1-mini')
    conflict_type : str
        Either 'within' for within-group conflicts or 'cross' for cross-group conflicts
    functional_type : str
        Either 'functional' or 'non_functional'
    validity_type : str, optional
        Either 'valid' for validated conflicts or 'valid_as_seen' for conflicts marked as seen but invalid,
        defaults to 'valid'
    """
    if not system_name or not persona_combination or not model_name:
        return []
    
    try:
        # Map validity_type to the corresponding directory name
        if validity_type == "valid":
            prefix = ""  # No prefix for valid conflicts
        elif validity_type == "valid_as_seen":
            prefix = "invalid_"
        else:
            print(f"Invalid validity type: {validity_type}")
            return []
            
        # Determine which conflicts directory to use
        conflict_dir = f"{prefix}conflicts_within_one_group" if conflict_type == "within" else f"{prefix}conflicts_across_two_groups"
        
        # Base path to conflicts directory for the specified model
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", system_name, persona_combination, model_name, "user_story_conflicts", conflict_dir
        )
        
        # Check if the conflict directory exists
        if not os.path.exists(base_path):
            print(f"Conflict directory not found: {base_path}")
            return []
            
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
def load_user_story_data(system_name, persona_combination, model_name):
    """Load and combine user story data from all files in the selected model directory"""
    if not system_name or not persona_combination or not model_name:
        return "No model selected."
    
    try:
        # Path to the user stories directory for the specified model
        user_stories_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", system_name, persona_combination, model_name, "user_stories"
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
            return f"No user story data found for model: {persona_combination}/{model_name}"
    except Exception as e:
        return f"Error loading user stories: {str(e)}"

# Function to load conflict data from a specific model and type
def load_conflict_data(system_name, persona_combination, model_name, conflict_type, functional_type, validity_type="valid"):
    """Load conflict data based on model, conflict type (within/cross), functional type and validity type
    
    Parameters:
    -----------
    system_name : str
        The system name (e.g., 'alfred')
    persona_combination : str
        The persona combination folder name
    model_name : str
        The model name (e.g., 'gpt-4.1-mini')
    conflict_type : str
        Either 'within' for within-group conflicts or 'cross' for cross-group conflicts
    functional_type : str
        Either 'functional' or 'non_functional'
    validity_type : str, optional
        Either 'valid' for validated conflicts or 'valid_as_seen' for conflicts marked as seen but invalid,
        defaults to 'valid'
    """
    if not system_name or not persona_combination or not model_name:
        return "No model selected."
    
    try:
        # Map validity_type to the corresponding directory name
        if validity_type == "valid":
            prefix = ""  # No prefix for valid conflicts
        elif validity_type == "valid_as_seen":
            prefix = "invalid_"
        else:
            return f"Invalid validity type: {validity_type}"
            
        # Determine which conflicts directory to use
        conflict_dir = f"{prefix}conflicts_within_one_group" if conflict_type == "within" else f"{prefix}conflicts_across_two_groups"
        
        # Base path to conflicts directory for the specified model
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", system_name, persona_combination, model_name, "user_story_conflicts", conflict_dir
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
            validity_label = "valid" if validity_type == "valid" else "invalid"
            conflict_type_label = "within-group" if conflict_type == "within" else "cross-group"
            return f"No {validity_label} {conflict_type_label} {functional_type} conflict data found for model: {persona_combination}/{model_name}"
    except Exception as e:
        return f"Error loading conflicts: {str(e)}"

def get_user_story_files(system_name, persona_combination, model_name):
    """Get list of user story files for a specific model"""
    if not system_name or not persona_combination or not model_name:
        return []
    
    try:
        # Path to the user stories directory for the specified model
        user_stories_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", system_name, persona_combination, model_name, "user_stories"
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

def load_single_user_story_file(system_name, persona_combination, model_name, filename):
    """Load a single user story file"""
    if not system_name or not persona_combination or not model_name or not filename:
        return "No file selected."
    
    try:
        # Path to the specific user story file
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", system_name, persona_combination, model_name, "user_stories", filename
        )
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return f"File not found: {filename}"
    except Exception as e:
        return f"Error loading file: {str(e)}"

def load_single_conflict_file(system_name, persona_combination, model_name, conflict_type, functional_type, filename, validity_type="valid"):
    """Load a single conflict file
    
    Parameters:
    -----------
    system_name : str
        The system name (e.g., 'alfred')
    persona_combination : str
        The persona combination folder name
    model_name : str
        The model name (e.g., 'gpt-4.1-mini')
    conflict_type : str
        Either 'within' for within-group conflicts or 'cross' for cross-group conflicts
    functional_type : str
        Either 'functional' or 'non_functional'
    filename : str
        The JSON filename to load
    validity_type : str, optional
        Either 'valid' for validated conflicts or 'valid_as_seen' for conflicts marked as seen but invalid,
        defaults to 'valid'
    """
    if not system_name or not persona_combination or not model_name or not filename:
        return "No file selected."
    
    try:
        # Map validity_type to the corresponding directory name
        if validity_type == "valid":
            prefix = ""  # No prefix for valid conflicts
        elif validity_type == "valid_as_seen":
            prefix = "invalid_"
        else:
            return f"Invalid validity type: {validity_type}"
            
        # Determine which conflicts directory to use
        conflict_dir = f"{prefix}conflicts_within_one_group" if conflict_type == "within" else f"{prefix}conflicts_across_two_groups"
        
        # Base path to conflicts directory for the specified model
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", system_name, persona_combination, model_name, "user_story_conflicts", conflict_dir
        )
        
        # Check if the directory exists
        if not os.path.exists(base_path):
            conflict_type_label = "within-group" if conflict_type == "within" else "cross-group"
            return f"Conflict directory not found for {conflict_type_label}"
        
        # Determine the directory based on functional vs non-functional
        sub_dir = "functional_user_stories" if functional_type == "functional" else "non_functional_user_stories"
        conflicts_path = os.path.join(base_path, sub_dir)
        
        # Check if the subdirectory exists
        if not os.path.exists(conflicts_path):
            return f"{functional_type} directory not found in {conflict_dir}"
        
        # Path to the specific conflict file
        file_path = os.path.join(conflicts_path, filename)
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return f"File not found: {filename}"
    except Exception as e:
        return f"Error loading file: {str(e)}"

def load_conflict_from_custom_dir(custom_dir, filename):
    """Load a conflict file from a custom directory (for future cross-group conflicts)"""
    if not custom_dir or not filename or not os.path.exists(custom_dir):
        return "Directory not found or no file selected."
    
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

def create_user_stories_zip(system_name, persona_combination, model_name):
    """Create a zip file containing all user story files for a model"""
    if not system_name or not persona_combination or not model_name:
        return None, "No model selected."
    
    try:
        # Path to the user stories directory for the specified model
        user_stories_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", system_name, persona_combination, model_name, "user_stories"
        )
        
        if not os.path.exists(user_stories_path):
            return None, f"User stories directory not found for model: {persona_combination}/{model_name}"
        
        # Create a zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add each JSON file to the zip
            for file_name in os.listdir(user_stories_path):
                if file_name.endswith('.json') and not file_name.endswith('.bak'):
                    file_path = os.path.join(user_stories_path, file_name)
                    zip_file.write(file_path, file_name)
        
        # Reset the buffer position to the beginning
        zip_buffer.seek(0)
        return zip_buffer, None
    except Exception as e:
        return None, f"Error creating zip file: {str(e)}"

def create_conflicts_zip(system_name, persona_combination, model_name, conflict_type, functional_type, validity_type="valid"):
    """Create a zip file containing all conflict files for a model and type"""
    if not system_name or not persona_combination or not model_name:
        return None, "No model selected."
    
    try:
        # Map validity_type to the corresponding directory name
        if validity_type == "valid":
            prefix = ""  # No prefix for valid conflicts
        elif validity_type == "valid_as_seen":
            prefix = "invalid_"
        else:
            return None, f"Invalid validity type: {validity_type}"
            
        # Determine which conflicts directory to use
        conflict_dir = f"{prefix}conflicts_within_one_group" if conflict_type == "within" else f"{prefix}conflicts_across_two_groups"
        
        # Base path to conflicts directory for the specified model
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "results", system_name, persona_combination, model_name, "user_story_conflicts", conflict_dir
        )
        
        # Check if the conflict directory exists
        if not os.path.exists(base_path):
            conflict_type_label = "within-group" if conflict_type == "within" else "cross-group"
            return None, f"{conflict_type_label} conflicts directory not found for model: {persona_combination}/{model_name}"
        
        # Determine the directory based on functional vs non-functional
        sub_dir = "functional_user_stories" if functional_type == "functional" else "non_functional_user_stories"
        conflicts_path = os.path.join(base_path, sub_dir)
        
        if not os.path.exists(conflicts_path):
            conflict_type_label = "within-group" if conflict_type == "within" else "cross-group"
            return None, f"{conflict_type_label} {functional_type} conflicts directory not found for model: {persona_combination}/{model_name}"
        
        # Create a zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add each JSON file to the zip
            for file_name in os.listdir(conflicts_path):
                if file_name.endswith('.json'):
                    file_path = os.path.join(conflicts_path, file_name)
                    zip_file.write(file_path, file_name)
        
        # Reset the buffer position to the beginning
        zip_buffer.seek(0)
        return zip_buffer, None
    except Exception as e:
        return None, f"Error creating zip file: {str(e)}"

def save_api_key_to_file(api_key):
    """Save API key to a file for use by the utils module"""
    try:
        # Path to the parent directory of this file
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        api_key_path = os.path.join(project_root, "api_key.txt")
        
        # Write API key to file
        with open(api_key_path, 'w') as f:
            f.write(api_key)
        return True
    except Exception as e:
        print(f"Error saving API key: {str(e)}")
        return False


def run_pipeline(api_key, model_id=None, system_name="alfred"):
    """Run the pipeline script in a separate process and capture output"""
    
    # Initialize a queue for storing process output
    if 'output_queue' not in st.session_state:
        st.session_state.output_queue = Queue()

    # Initialize log content if not already done
    if 'log_content' not in st.session_state:
        st.session_state.log_content = ""
    
    # Clear any previous process
    if 'process' in st.session_state and st.session_state.process is not None:
        try:
            st.session_state.process.terminate()
        except:
            pass
        st.session_state.process = None

    # Mark process as not running
    st.session_state.process_running = False
    
    # Path to the main pipeline script
    pipeline_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "run_pipeline.py"
    )
    
    # Working directory (parent directory of this script)
    working_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Define a function to read process output
    def read_output(process, queue):
        """Read output from process and put it in the queue"""
        try:
            for line in iter(process.stdout.readline, b''):
                if line:
                    decoded_line = line.decode('utf-8')
                    queue.put(decoded_line)
                    # Print to the console for debugging
                    print(f"Pipeline output: {decoded_line.strip()}", flush=True)
                else:
                    break
        except Exception as e:
            queue.put(f"Error reading process output: {str(e)}\n")
        finally:
            process.stdout.close()
    
    try:
        # Construct the command to run the pipeline
        command = [sys.executable, pipeline_path]
        
        # Add the model ID as an argument if provided
        if model_id:
            command.extend(["--model", model_id])  # Pass model as command-line argument
            st.session_state.log_content += f"Running pipeline with model: {model_id}\n"
        
        # Start the process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=False,
            cwd=working_dir
        )
        
        # Store the process in the session state
        st.session_state.process = process
        st.session_state.process_running = True
        
        # Start thread to read output
        output_thread = threading.Thread(target=read_output, args=(process, st.session_state.output_queue))
        output_thread.daemon = True  # Thread will exit when main program exits
        output_thread.start()
        
        return True
    except Exception as e:
        st.session_state.log_content += f"Error starting pipeline: {str(e)}\n"
        return False

def stop_pipeline():
    """Stop the running pipeline process"""
    if st.session_state.process is not None and st.session_state.process_running:
        try:
            st.session_state.log_content += "\nStopping process...\n"
            # Try to terminate gracefully first
            st.session_state.process.terminate()
            # Wait a bit for it to terminate
            time.sleep(1)
            # If it's still running, kill it
            if st.session_state.process.poll() is None:
                st.session_state.process.kill()
            
            st.session_state.process_running = False
            st.session_state.log_content += "Process stopped.\n"
            return True
        except Exception as e:
            st.session_state.log_content += f"\nError stopping process: {str(e)}\n"
            return False
    return True

def update_log_from_queue():
    """Update log content from the output queue"""
    update_occurred = False
    # Check if there's any output to process
    if hasattr(st.session_state, 'output_queue') and not st.session_state.output_queue.empty():
        # Add all lines to the log content
        new_lines = []
        while not st.session_state.output_queue.empty():
            line = st.session_state.output_queue.get()
            new_lines.append(line)
        
        # Update the log content with new lines
        if new_lines:
            st.session_state.log_content += ''.join(new_lines)
            update_occurred = True
        
        # Check if the process has completed
        if st.session_state.process and st.session_state.process.poll() is not None:
            exit_code = st.session_state.process.returncode
            st.session_state.log_content += f"\nProcess completed with exit code: {exit_code}\n"
            st.session_state.process_running = False
            update_occurred = True
            st.rerun()
    
    # Even if the queue is empty, check if the process has completed
    elif hasattr(st.session_state, 'process') and st.session_state.process_running and st.session_state.process and st.session_state.process.poll() is not None:
        exit_code = st.session_state.process.returncode
        st.session_state.log_content += f"\nProcess completed with exit code: {exit_code}\n"
        st.session_state.process_running = False
        update_occurred = True
        st.rerun()
    
    return update_occurred


def test_model_connection(model_id, api_key=None):
    """Test OpenAI API connection with the selected model"""
    try:
        # Import utils here to avoid loading at module import time
        import pipeline.utils as utils
        import importlib
        importlib.reload(utils)
        
        # Create an instance of Utils to use its methods
        utils_instance = utils.Utils()
        
        # If an API key is provided, use it directly
        if api_key:
            utils_instance.api_key = api_key
        else:
            # Try to load the API key from file
            try:
                utils_instance.load_api_key()
            except Exception as e:
                return False, f"Failed to load API key: {str(e)}"
        
        # Make sure we have a valid API key
        if not utils_instance.api_key:
            return False, "No API key available. Please enter your API key first."
        
        # Test a simple prompt with the model using the Utils instance
        test_response = utils_instance.get_llm_response("Hello, this is a test prompt to verify the connection.")
        
        # guard against a None or non-string response
        if not isinstance(test_response, str):
            return False, f"Connection test failed: no valid response (got {test_response!r})"
        if "❌" in test_response or "Error" in test_response:
            return False, f"Connection test failed: {test_response}"
        
        return True, "Successfully connected to OpenAI API with the selected model"
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        return False, f"Error testing model connection: {str(e)}\n{error_traceback}"

def process_with_api(api_key, model_name, system_name="alfred"):
    """Process the inputs using the API based on selected model and run the main.py pipeline"""
    
    # Verify the API key exists
    if not api_key or len(api_key.strip()) == 0:
        return "No API key provided. Please enter or upload an API key first.", False
    
    # Save API key to file for the utils functions
    if not save_api_key_to_file(api_key):
        return "Failed to save API key", False
        
    try:
        # Force reload the utils module to ensure latest version is loaded
        print("Reloading utils module...")
        import sys
        import importlib

        # Remove any existing utils module from sys.modules to force a complete reload
        if "pipeline.utils" in sys.modules:
            del sys.modules["pipeline.utils"]

        # Now import the module fresh
        import pipeline.utils as utils
        
        # Now that we've saved the API key, set it directly in the utils module
        try:
            print("Setting API key directly...")
            utils.api_key = api_key
        except Exception as e:
            # If direct setting doesn't work, try alternative methods
            if hasattr(utils, 'update_api_key'):
                try:
                    print("Using update_api_key function...")
                    utils.update_api_key(api_key)  
                except Exception as api_e:
                    print(f"Error using update_api_key: {api_e}")
            # Fallback method if function not found
            utils.client = utils.OpenAI(api_key=api_key)
        except Exception as e:
            error_message = f"Error setting API key: {str(e)}"
            print(error_message)
            return error_message, False
        
        # Set the model in utils.py before running the pipeline
        model_id = model_name
        print(f"Setting model to: {model_id}")
        
        utils_instance = utils.Utils()
        utils_instance.set_model(model_id)
            
        # Update dependent path variables that rely on CURRENT_LLM
        utils.USE_CASE_DIR = os.path.join("results", model_id, "use_cases")
        utils.USE_CASE_TASK_EXTRACTION_DIR = os.path.join("results", model_id, "use_case_task_extraction")
        utils.USER_STORY_DIR = os.path.join("results", model_id, "user_stories")
            
        # Update the conflict directories
        conflict_base = os.path.join("results", model_id)
        if hasattr(utils, 'USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR'):
            utils.USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(conflict_base, "conflicts_within_one_group")
                
            # Set the functional and non-functional subdirectories if they exist
            if hasattr(utils, 'FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR'):
                utils.FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(
                    utils.USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, "functional_user_stories"
                )
            if hasattr(utils, 'NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR'):
                utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(
                    utils.USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, "non_functional_user_stories"
                )
        
        print(f"Current LLM after setting: {utils_instance.CURRENT_LLM}")
        
        # Test connection to make sure the model works
        print("Testing connection with the selected model...")
        connection_success, connection_message = test_model_connection(model_id, api_key)
        if not connection_success:
            print(f"Model connection test failed: {connection_message}")
            return connection_message, False
        
        print("Model connection test successful")
        
        # Start the pipeline in a background process
        print("Starting run_pipeline...")
        if run_pipeline(api_key, model_id):
            print("Pipeline started successfully")
            return "Pipeline started successfully", True
        else:
            print("Failed to start pipeline")
            return "Failed to start pipeline", False
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_message = f"Error during processing: {str(e)}\nTraceback: {error_traceback}"
        print(error_message)
        return error_message, False

def limit_words(text, limit=25):
    """Limit text to specified number of words"""
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]) + "..."

# --- Page Configuration ---
st.set_page_config(
    page_title="Design to Streamlit App",
    layout="wide",  # Use wide layout for better use of space
)

# --- Sidebar ---
with st.sidebar:
    st.header("Configuration")

    # Function to load the existing API key from file
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

    # Get the existing API key from the file
    existing_api_key = load_existing_api_key()

    # Display the API key in the input field with automatic saving on change
    api_key = st.text_input(
        "API Key Input", 
        value=existing_api_key,
        type="password",
        help="Enter your OpenAI API key. It will be saved locally for future use."
    )

    # Save API key when changed
    if api_key != existing_api_key:
        if api_key:  # Only save if not empty
            # Import the update_api_key function if available
            try:
                import pipeline.api_utils as api_utils
                new_api_key = api_utils.update_api_key(api_key)
                if new_api_key:
                    st.success("✅ API key loaded and saved successfully!")
                else:
                    st.error("❌ Failed to save API key")
            except ImportError:
                # Fall back to basic file save if module not found
                if save_api_key_to_file(api_key):
                    st.success("✅ API key saved successfully!")
                else:
                    st.error("❌ Failed to save API key to file")
    
    # Show active status if key exists
    if api_key:
        st.info("API Key is ready to use.")
    else:
        st.warning("No API Key provided yet.")
    
    st.markdown("---") # Separator
    
    # Model selection
    st.subheader("Model Selection")
    model_options = ["gpt-4.1-mini", "gpt-4o-mini"]
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
    
    # First level selection - system category
    system_categories = ["alfred"]  # Define categories, can expand in the future
    selected_system_summary = st.selectbox("Choose a system category", system_categories, index=0, key="system_category")
    
    if selected_system_summary:
        # Load and display the system summary
        system_summary = get_cached_system_summary(selected_system_summary)
        st.markdown("**System Summary:**")
        st.info(limit_words(system_summary))

# --- Action Buttons ---
col_actions_1, col_actions_2 = st.columns(2)

with col_actions_1:
    # Process button that will send data to the API and start the pipeline
    # Disable the button if a process is already running
    if 'process_running' not in st.session_state:
        st.session_state.process_running = False
        
    if st.button("Process Inputs", type="primary", disabled=st.session_state.process_running):
        if not api_key:
            st.warning("Please enter your API key first.")
        elif not selected_system_summary:
            st.warning("Please select a system summary.")
        else:
            # Initialize log content if needed
            if 'log_content' not in st.session_state:
                st.session_state.log_content = ""
                
            # Add initial information to the log
            from datetime import datetime
            st.session_state.log_content = f"--- Processing started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n"
            st.session_state.log_content += f"Model selected: {selected_model}\n"
            st.session_state.log_content += "Initializing pipeline (this may take a minute)...\n"
            
            # # Update the log immediately to show some activity
            # result_log_placeholder = st.empty()
            # result_log_placeholder.text_area("Log Output", st.session_state.log_content, height=400, disabled=True, key="initial_log")
            
            # Run in a try-except block to catch errors
            with st.spinner("Processing..."):
                try:
                    # Call the API processing function
                    result, success = process_with_api(
                        api_key=api_key,
                        model_name=selected_model,
                        system_name=selected_system_summary
                    )
                    
                    # Add the result to the log
                    st.session_state.log_content += f"\n{result}\n"
                    
                    if not success:
                        st.warning(f"Processing issue: {result}")
                except Exception as e:
                    st.session_state.log_content += f"Exception in processing: {str(e)}\n"
                    st.error(f"Processing failed: {str(e)}")

with col_actions_2:
    # Stop button to terminate the pipeline process
    if st.button("Stop Process", disabled=not st.session_state.get('process_running', False)):
        if stop_pipeline():
            # Force a page refresh to update the Process Inputs button state
            st.rerun()

col_actions_3, _ = st.columns([1, 3])
with col_actions_3:
    if st.button("Clear Log"):
        st.session_state.log_content = ""
        st.rerun()

# Replace the Auto-refresh section after line 870 with:

# --- Result Log ---
st.subheader("Processing Log")

# Initialize log settings if needed
if 'log_content' not in st.session_state:
    st.session_state.log_content = ""
    
if 'process_running' not in st.session_state:
    st.session_state.process_running = False

if 'auto_scroll' not in st.session_state:
    st.session_state.auto_scroll = True

# Option to pause/resume auto-scrolling
if st.session_state.process_running:
    col_scroll1, col_scroll2 = st.columns([1, 3])
    with col_scroll1:
        scroll_label = "Disable Auto-Scroll" if st.session_state.auto_scroll else "Enable Auto-Scroll"
        # Use a unique key for the button to ensure it works consistently
        if st.button(scroll_label, key="toggle_auto_scroll"):
            # Toggle the auto-scroll state
            st.session_state.auto_scroll = not st.session_state.auto_scroll
            # Force an immediate rerun to update UI without waiting for auto-refresh
            st.rerun()
    
    with col_scroll2:
        scroll_status = "📜 Auto-scrolling enabled (follows new logs)" if st.session_state.auto_scroll else "🔒 Auto-scrolling disabled (view stays in place)"
        st.info(scroll_status)

# Auto-update the log content from the queue while the process is running
if st.session_state.process_running:
    update_occurred = update_log_from_queue()

# Create a placeholder for the log content
result_log_placeholder = st.empty() # Placeholder for dynamic content

# Display the log content
if st.session_state.log_content:
    # Generate a random key for this refresh cycle to avoid caching
    # Use a fixed key when auto-scroll is disabled to preserve position
    from datetime import datetime
    if st.session_state.auto_scroll:
        refresh_key = f"refresh_{datetime.now().timestamp()}"
    else:
        refresh_key = "fixed_log_key"
    
    # Display the log content with auto-scroll to bottom behavior
    log_content = st.session_state.log_content
    # Count lines to determine proper height (with a min/max)
    num_lines = log_content.count('\n') + 1
    height = min(max(400, num_lines * 20), 600)  # Adjust multiplier as needed
    
    # Display the log content
    result_log_placeholder.text_area("Log Output", log_content, height=height, disabled=True, key=refresh_key)

# Auto-refresh while the process is running
if st.session_state.process_running:
    # Update log more frequently but rerun less frequently based on auto-scroll setting
    update_occurred = update_log_from_queue()
    
    # Display status information
    with st.container():
        last_update = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        st.markdown(f"**Process running** · Last update: {last_update}")
        
        # Display spinning indicator to show activity
        with st.spinner("Processing..."):
            # Use longer sleep time when auto-scroll is disabled
            if st.session_state.auto_scroll:
                # Dynamic sleep time based on updates
                if update_occurred:
                    time.sleep(0.3)
                else:
                    time.sleep(1.0)
                st.rerun()
            else:
                # When auto-scroll disabled, wait longer between refreshes
                time.sleep(3.0)
                if update_occurred:
                    st.rerun()  # Only rerun if there were updates
                    
# --- Results Section ---
st.subheader("Results & Downloads")

# First level: Get available systems from results directory
results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
available_systems = []

try:
    if os.path.exists(results_dir):
        available_systems = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))]
except Exception as e:
    print(f"Error getting available systems: {str(e)}")

# System selection dropdown
if available_systems:
    selected_system = st.selectbox(
        "Select System", 
        options=available_systems,
        help="Choose which system's results to display"
    )
    
    # Second level: Get persona combinations for the selected system
    system_path = os.path.join(results_dir, selected_system)
    available_persona_combinations = []
    
    try:
        if os.path.exists(system_path):
            available_persona_combinations = [d for d in os.listdir(system_path) 
                                           if os.path.isdir(os.path.join(system_path, d))]
    except Exception as e:
        print(f"Error getting persona combinations for {selected_system}: {str(e)}")
    
    # Persona combination selection for results
    if available_persona_combinations:
        selected_persona_combination = st.selectbox(
            "Select Persona Combination", 
            options=available_persona_combinations,
            help="Choose which persona combination's results to display"
        )
    
    # Get models for the selected persona combination
    if selected_persona_combination:
        available_models_for_persona = get_models_for_persona(selected_system, selected_persona_combination)
        
        if available_models_for_persona:
            # Add a refresh button next to the dropdown
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_model_name = st.selectbox(
                    "Select Model", 
                    options=available_models_for_persona,
                    help="Choose which model's results to display for this persona combination"
                )
            with col2:
                if st.button("🔄 Refresh Models"):
                    # Clear the cache for the get_models_for_persona function
                    get_models_for_persona.clear()
                    st.rerun()
            
            # Add dropdown for validity type (valid or valid_as_seen/invalid)
            validity_options = ["Valid Conflicts", "Invalid Conflicts"]
            selected_validity_type = st.selectbox(
                "Select Validity Type",
                options=validity_options,
                help="Choose whether to view valid conflicts or invalid-but-seen conflicts"
            )
            # Map the display name to the internal value
            validity_type = "valid" if selected_validity_type == "Valid Conflicts" else "valid_as_seen"
        else:
            st.warning(f"No models found for persona combination: {selected_persona_combination}")
            selected_model_name = None
            validity_type = "valid"  # Default
    else:
        selected_model_name = None
        validity_type = "valid"  # Default
else:
    st.warning("No persona combination results found in the results directory.")
    selected_persona_combination = None
    selected_model_name = None
    validity_type = "valid"  # Default

# Only display results if a valid persona combination and model are selected
if selected_persona_combination and selected_model_name:
    col_results_1, col_results_2 = st.columns([1,2]) # Adjust column widths as needed

    with col_results_1:
        st.markdown("##### User Stories")
        
        # Load actual user story data if a model is selected
        # Get list of individual user story files
        user_story_files = get_user_story_files(selected_system, selected_persona_combination, selected_model_name)
        
        # Combined download option
        user_stories_data = load_user_story_data(selected_system, selected_persona_combination, selected_model_name)
        st.download_button(
            label="All User Stories (Combined)",
            data=user_stories_data,
            file_name=f"{selected_persona_combination}_{selected_model_name}_user_stories.json",
            mime="application/json",
        )
        
        # Zip file download option
        zip_buffer, zip_error = create_user_stories_zip(selected_system, selected_persona_combination, selected_model_name)
        if zip_buffer:
            st.download_button(
                label="Download All Files (ZIP)",
                data=zip_buffer,
                file_name=f"{selected_persona_combination}_{selected_model_name}_user_stories.zip",
                mime="application/zip",
                key="zip_download"
            )
        elif zip_error:
            st.warning(zip_error)
            
        # List individual files with download options
        if user_story_files:
            st.markdown("##### Individual User Story Files")
            for file_name in user_story_files:
                file_data = load_single_user_story_file(selected_system, selected_persona_combination, selected_model_name, file_name)
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
            st.info("No user story files found for the selected model.")

    with col_results_2:
        st.markdown("##### Conflict Analysis")

        # Within Group Conflicts
        st.markdown("###### Within Group Conflicts")
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            st.markdown("**Functional Conflicts**")
            # Load actual conflict data
            within_functional_data = load_conflict_data(
                selected_system,
                selected_persona_combination,
                selected_model_name, 
                "within", 
                "functional",
                validity_type
            )
            # Combined download option
            st.download_button(
                label="All Functional Conflicts (Combined)",
                data=within_functional_data,
                file_name=f"{selected_persona_combination}_{selected_model_name}_conflict_within_functional.json",
                mime="application/json",
                key="within_functional" # Unique key for each button
            )
            
            # Zip file download option
            zip_buffer, zip_error = create_conflicts_zip(
                selected_system,
                selected_persona_combination,
                selected_model_name, 
                "within", 
                "functional",
                validity_type
            )
            if zip_buffer:
                st.download_button(
                    label="All Functional Files (ZIP)",
                    data=zip_buffer,
                    file_name=f"{selected_persona_combination}_{selected_model_name}_conflicts_within_functional.zip",
                    mime="application/zip",
                    key="within_functional_zip"
                )
            elif zip_error:
                st.warning(zip_error)
                
            # List individual files with download options
            functional_files = get_conflict_files(selected_system, selected_persona_combination, selected_model_name, "within", "functional", validity_type)
            if functional_files:
                st.markdown("**Individual Conflict Files:**")
                for file_name in functional_files:
                    file_data = load_single_conflict_file(
                        selected_system,
                        selected_persona_combination,
                        selected_model_name, 
                        "within", 
                        "functional", 
                        file_name,
                        validity_type
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
                st.info("No functional conflict files found for the selected model.")
            
        with sub_col2:
            st.markdown("**Non-Functional Conflicts**")
            # Load actual conflict data
            within_non_functional_data = load_conflict_data(
                selected_system,
                selected_persona_combination,
                selected_model_name, 
                "within", 
                "non_functional",
                validity_type
            )
            # Combined download option
            st.download_button(
                label="All Non-Functional Conflicts (Combined)",
                data=within_non_functional_data,
                file_name=f"{selected_persona_combination}_{selected_model_name}_conflict_within_non_functional.json",
                mime="application/json",
                key="within_non_functional"
            )
            
            # Zip file download option
            zip_buffer, zip_error = create_conflicts_zip(
                selected_system,
                selected_persona_combination,
                selected_model_name, 
                "within", 
                "non_functional",
                validity_type
            )
            if zip_buffer:
                st.download_button(
                    label="All Non-Functional Files (ZIP)",
                    data=zip_buffer,
                    file_name=f"{selected_persona_combination}_{selected_model_name}_conflicts_within_non_functional.zip",
                    mime="application/zip",
                    key="within_non_functional_zip"
                )
            elif zip_error:
                print(f"Error creating zip: {zip_error}")
                
            # List individual files with download options
            non_functional_files = get_conflict_files(selected_system, selected_persona_combination, selected_model_name, "within", "non_functional", validity_type)
            if non_functional_files:
                st.markdown("**Individual Conflict Files:**")
                for file_name in non_functional_files:
                    file_data = load_single_conflict_file(
                        selected_system,
                        selected_persona_combination,
                        selected_model_name, 
                        "within", 
                        "non_functional", 
                        file_name,
                        validity_type
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
                st.info("No non-functional conflict files found for the selected model.")

        st.markdown("---") # Visual separator within the column

        # Cross Group Conflicts
        st.markdown("###### Cross Group Conflicts")
        
        # Get functional and non-functional files for cross-group conflicts
        functional_cross_files = get_conflict_files(selected_system, selected_persona_combination, selected_model_name, "cross", "functional", validity_type)
        non_functional_cross_files = get_conflict_files(selected_system, selected_persona_combination, selected_model_name, "cross", "non_functional", validity_type)
        
        if functional_cross_files or non_functional_cross_files:
            sub_cross_col1, sub_cross_col2 = st.columns(2)
            
            with sub_cross_col1:
                st.markdown("**Functional Conflicts**")
                # Load actual conflict data
                cross_functional_data = load_conflict_data(
                    selected_system,
                    selected_persona_combination,
                    selected_model_name, 
                    "cross", 
                    "functional",
                    validity_type
                )
                # Combined download option
                st.download_button(
                    label="All Cross-Group Functional Conflicts",
                    data=cross_functional_data,
                    file_name=f"{selected_persona_combination}_{selected_model_name}_conflict_cross_functional.json",
                    mime="application/json",
                    key="cross_functional" # Unique key for each button
                )
                
                # Zip file download option
                zip_buffer, zip_error = create_conflicts_zip(
                    selected_system,
                    selected_persona_combination,
                    selected_model_name, 
                    "cross", 
                    "functional",
                    validity_type
                )
                if zip_buffer:
                    st.download_button(
                        label="All Cross-Group Functional Files (ZIP)",
                        data=zip_buffer,
                        file_name=f"{selected_persona_combination}_{selected_model_name}_conflicts_cross_functional.zip",
                        mime="application/zip",
                        key="cross_functional_zip"
                    )
                elif zip_error:
                    st.warning(zip_error)
                
                # List individual files with download options
                if functional_cross_files:
                    st.markdown("**Individual Cross-Group Conflict Files:**")
                    for file_name in functional_cross_files:
                        file_data = load_single_conflict_file(
                            selected_system,
                            selected_persona_combination,
                            selected_model_name, 
                            "cross", 
                            "functional", 
                            file_name,
                            validity_type
                        )
                        # Use horizontal layout without nested columns
                        st.write(f"{file_name} ", 
                                st.download_button(
                                    label="Download",
                                    data=file_data,
                                    file_name=file_name,
                                    mime="application/json",
                                    key=f"download_cross_func_{file_name}"
                                )
                        )
                else:
                    st.info("No cross-group functional conflict files found for the selected model.")
                
            with sub_cross_col2:
                st.markdown("**Non-Functional Conflicts**")
                # Load actual conflict data
                cross_non_functional_data = load_conflict_data(
                    selected_system,
                    selected_persona_combination,
                    selected_model_name, 
                    "cross", 
                    "non_functional",
                    validity_type
                )
                # Combined download option
                st.download_button(
                    label="All Cross-Group Non-Functional Conflicts",
                    data=cross_non_functional_data,
                    file_name=f"{selected_persona_combination}_{selected_model_name}_conflict_cross_non_functional.json",
                    mime="application/json",
                    key="cross_non_functional"
                )
                
                # Zip file download option
                zip_buffer, zip_error = create_conflicts_zip(
                    selected_system,
                    selected_persona_combination,
                    selected_model_name, 
                    "cross", 
                    "non_functional",
                    validity_type
                )
                if zip_buffer:
                    st.download_button(
                        label="All Cross-Group Non-Functional Files (ZIP)",
                        data=zip_buffer,
                        file_name=f"{selected_persona_combination}_{selected_model_name}_conflicts_cross_non_functional.zip",
                        mime="application/zip",
                        key="cross_non_functional_zip"
                    )
                elif zip_error:
                    st.warning(zip_error)
                
                # List individual files with download options
                if non_functional_cross_files:
                    st.markdown("**Individual Cross-Group Conflict Files:**")
                    for file_name in non_functional_cross_files:
                        file_data = load_single_conflict_file(
                            selected_system,
                            selected_persona_combination,
                            selected_model_name, 
                            "cross", 
                            "non_functional", 
                            file_name,
                            validity_type
                        )
                        # Use horizontal layout without nested columns
                        st.write(f"{file_name} ", 
                                st.download_button(
                                    label="Download",
                                    data=file_data,
                                    file_name=file_name,
                                    mime="application/json",
                                    key=f"download_cross_nonfunc_{file_name}"
                                )
                        )
                else:
                    st.info("No cross-group non-functional conflict files found for the selected model.")
        else:
            st.info("No cross-group conflicts found for the selected model and persona combination.")

# --- Footer (Optional) ---
st.markdown("---")
st.caption("ALFRED User Story Analysis Interface - Results can be viewed and downloaded from different AI models.")
