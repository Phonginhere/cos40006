import json
import os

from typing import List, Dict, Optional


# ===============================================================================================
# CONSTANTS

# Base directory - path to the src directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Global variable to specify which LLM is being used in the pipeline
CURRENT_LLM = "gpt-4o-mini"  # Default model, will be updated from API call

# Function to load API key from file
def load_api_key():
    api_key_path = os.path.join(BASE_DIR, "openai_api_key.txt")
    if os.path.exists(api_key_path):
        with open(api_key_path, "r") as f:
            api_key = f.read().strip()
            os.environ["OPENAI_API_KEY"] = api_key
            return api_key
    else:
        raise FileNotFoundError(f"API key file not found at: {api_key_path}")

SYSTEM_NAME = "alfred"

USER_GROUP_KEYS = {
    "Developers and App Creators": "group_1",
    "Caregivers and Medical Staff": "group_2",
    "Older Adults": "group_3",
}

USER_GROUPS = list(USER_GROUP_KEYS.keys())

# Use absolute paths based on the BASE_DIR
SYSTEM_SUMMARY_PATH = os.path.join(BASE_DIR, "data", SYSTEM_NAME, "system_summary.txt")
USER_GROUP_SUMMARY_DIR = os.path.join(BASE_DIR, "data", SYSTEM_NAME, "group_summaries")
PERSONA_DIR = os.path.join(BASE_DIR, "data", SYSTEM_NAME, "personas")

USE_CASE_SUMMARY_PATH = os.path.join(BASE_DIR, "data", SYSTEM_NAME, "use_case_rules", "use_case_summary.txt")
USE_CASE_TYPE_CONFIG_PATH = os.path.join(BASE_DIR, "data", SYSTEM_NAME, "use_case_rules", "use_case_type_config.json")
USE_CASE_TASK_ANALYSIS_EXAMPLE_PATH = os.path.join(BASE_DIR, "data", SYSTEM_NAME, "use_case_rules", "use_case_task_analysis_example.txt")

USER_STORY_SUMMARY_PATH = os.path.join(BASE_DIR, "data", SYSTEM_NAME, "user_story_rules", "user_story_summary.txt")
NON_FUNCTIONAL_USER_STORY_CLUSTERING_SUMMARY_DIR = os.path.join(BASE_DIR, "data", SYSTEM_NAME, "user_story_rules", "non_functional_user_story_clustering_summary")

NON_FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH = os.path.join(BASE_DIR, "data", SYSTEM_NAME, "user_story_conflict_rules", "non_functional_user_story_conflict_summary.txt")
FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH = os.path.join(BASE_DIR, "data", SYSTEM_NAME, "user_story_conflict_rules", "functional_user_story_conflict_summary.txt")

USE_CASE_DIR = os.path.join(BASE_DIR, "results", CURRENT_LLM, "use_cases")
USE_CASE_TASK_EXTRACTION_DIR = os.path.join(BASE_DIR, "results", CURRENT_LLM, "use_case_task_extraction")

USER_STORY_DIR = os.path.join(BASE_DIR, "results", CURRENT_LLM, "user_stories")
FUNCTIONAL_USER_STORY_CLUSTER_SET_PATH = os.path.join(BASE_DIR, "results", CURRENT_LLM, "functional_user_story_cluster_set.json")

NON_FUNCTIONAL_USER_STORY_ANALYSIS_PATH = os.path.join(BASE_DIR, "results", CURRENT_LLM, "non_functional_user_story_analysis.json")
NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(BASE_DIR, "results", CURRENT_LLM, "conflicts_within_one_group", "non_functional_user_stories")

FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(BASE_DIR, "results", CURRENT_LLM, "conflicts_within_one_group", "functional_user_stories")

# ==================================================================================================
# ALFRED SYSTEM SUMMARY LOADER

def load_system_summary() -> str:
    """Loads the ALFRED system summary from a plain text file."""
    try:
        with open(SYSTEM_SUMMARY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing ALFRED summary file: {SYSTEM_SUMMARY_PATH}")
    
# ==================================================================================================
# USER GROUP SUMMARY LOADER
def load_user_group_summary(group: str) -> str:
    """Loads the user group summary from a JSON file based on the user group."""
    summary_files = {
        value: os.path.join(USER_GROUP_SUMMARY_DIR, f"{value}_summary.json")
        for value in USER_GROUP_KEYS.values()
    }

    if group not in summary_files:
        raise ValueError(f"❌ Unknown user group: {group}. Valid options are: {', '.join(summary_files.keys())}")

    path = summary_files[group]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Create a formatted string that includes both summary and needs
            user_group_summary = f"Summary: {data['summary']}\n\nNeeds:\n"
            for need in data.get('needs', []):
                user_group_summary += f"- {need['title']}: {need['description']}\n"
            return user_group_summary
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ User group summary file not found: {path}")
    except json.JSONDecodeError:
        raise ValueError(f"❌ Error decoding JSON from file: {path}")
    
def load_all_user_group_summaries() -> Dict[str, str]:
    """Loads all user group summaries based on USER_GROUP_KEYS."""
    summaries = {}
    for group_label, group_key in USER_GROUP_KEYS.items():
        try:
            summaries[group_label] = load_user_group_summary(group_key)
        except Exception as e:
            print(f"⚠️ Could not load summary for '{group_label}' ({group_key}): {e}")
            summaries[group_label] = "(Missing summary)"
    return summaries

# ===============================================================================================
# USER GROUP MAPPING HELPERS

USER_GROUP_KEY_TO_NAME = {v: k for k, v in USER_GROUP_KEYS.items()}

def get_all_user_group_names() -> List[str]:
    """Returns a list of user group names like 'Older Adults'."""
    return list(USER_GROUP_KEYS.keys())

def get_all_user_group_keys() -> List[str]:
    """Returns a list of internal group keys like 'group_1'."""
    return list(USER_GROUP_KEYS.values())

def get_user_group_name_from_key(key: str) -> Optional[str]:
    """Maps 'group_1' → 'Developers and App Creators'."""
    return USER_GROUP_KEY_TO_NAME.get(key)

def get_user_group_key_from_name(name: str) -> Optional[str]:
    """Maps 'Older Adults' → 'group_3'. Case-insensitive and trimmed."""
    normalized = name.strip().lower()
    for label, key in USER_GROUP_KEYS.items():
        if label.lower() == normalized:
            return key
    return None
    
# ==================================================================================================
# USE CASE SUMMARY LOADER
def load_use_case_summary() -> str:
    try:
        with open(USE_CASE_SUMMARY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing use-case summary file at: {USE_CASE_SUMMARY_PATH}")
    
def load_use_case_task_example() -> str:
    try:
        with open(USE_CASE_TASK_ANALYSIS_EXAMPLE_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing use-case task analysis file at: {USE_CASE_TASK_ANALYSIS_EXAMPLE_PATH}")
    
# ==================================================================================================
# USER STORY SUMMARY LOADER
def load_user_story_summary() -> str:
    try:
        with open(USER_STORY_SUMMARY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing user story summary file at: {USER_STORY_SUMMARY_PATH}")

# ==================================================================================================
# NON-FUNCTIONAL USER STORY CLUSTER SUMMARY LOADER

def load_non_functional_user_story_cluster_summary(pillar: str) -> str:
    """Loads the pillar-specific cluster summary for user story classification."""
    path_map = {
        "General Requirements": "general_requirements_clusters_summary.txt",
        "Pillar 1 - User-Driven Interaction Assistant": "pillar_1_clusters_summary.txt",
        "Pillar 2 - Personalized Social Inclusion": "pillar_2_clusters_summary.txt",
        "Pillar 3 - Effective & Personalized Care": "pillar_3_clusters_summary.txt",
        "Pillar 4 - Physical & Cognitive Impairments Prevention": "pillar_4_clusters_summary.txt",
        "Developer Core": "developer_core_clusters_summary.txt"
    }
    filename = path_map.get(pillar)
    if not filename:
        return None

    full_path = os.path.join(NON_FUNCTIONAL_USER_STORY_CLUSTERING_SUMMARY_DIR, filename)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"❌ Cluster summary file not found: {full_path}")
        return None
    
# ==================================================================================================
# NON-FUNCTIONAL USER STORY CONFLICT SUMMARY LOADER
def load_non_functional_user_story_conflict_summary() -> str:
    try:
        with open(NON_FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing non-functional user story conflict summary file at: {NON_FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH}")

# ==================================================================================================
# LLM HANDLER

# Try to import OpenAI
try:
    from openai import OpenAI
except ImportError:
    raise ImportError("❌ Missing dependency: Please install the OpenAI package using 'pip install openai'.")

# Load OpenAI API key from file
def load_api_key():
    """Load API key from file"""
    # Try current directory first
    api_key_path = "openai_api_key.txt"
    
    # If not in current directory, try project root
    if not os.path.exists(api_key_path):
        api_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "openai_api_key.txt")
    
    if os.path.exists(api_key_path):
        with open(api_key_path, "r") as file:
            api_key = file.read().strip()
            os.environ["OPENAI_API_KEY"] = api_key
            return api_key
    else:
        raise FileNotFoundError("❌ API key file not found. Please create 'openai_api_key.txt' and add your API key.")

# Don't load the API key at module import time
# Instead, make client initialization lazy
client = None

def get_client():
    """Get or initialize the OpenAI client"""
    global client
    if client is None:
        from openai import OpenAI
        api_key = load_api_key()
        client = OpenAI(api_key=api_key)
    return client

# Generate a response using the Responses API
def get_openai_response(
    prompt: str,
    model: str = CURRENT_LLM,
    temperature: float = 0.7,
    system_prompt: str = "You are an expert in system requirements engineering."
) -> str:
    """Uses OpenAI's Responses API to generate a response from the specified model."""
    try:
        # Get or initialize the client
        client = get_client()
        
        response = client.responses.create(
            model=model,
            instructions=system_prompt,
            input=prompt,
            temperature=temperature,
        )

        # Use the SDK's shortcut to retrieve all text output
        return response.output_text.strip()

    except Exception as e:
        print(f"❌ OpenAI API Error: {e}")
        # Return a default string instead of None to avoid None.strip() errors
        return "Unknown"

# LLM Dispatcher
def get_llm_response(prompt: str) -> str:
    """Dispatches LLM call based on the currently selected model."""
    supported_models = ["gpt-4", "gpt-4o", "deepseek-coder", "cpt-4.0-mini", "gpt-4.1-mini"]
    
    # Check if any supported model prefix matches the current LLM
    if any(CURRENT_LLM.startswith(model_prefix) for model_prefix in supported_models):
        return get_openai_response(prompt, model=CURRENT_LLM)
    else:
        print(f"⚠️ Warning: Model '{CURRENT_LLM}' may not be fully supported. Attempting to use anyway.")
        return get_openai_response(prompt, model=CURRENT_LLM)

def set_current_llm(model_name):
    """Updates the current LLM model and refreshes all related file paths."""
    global CURRENT_LLM
    global USE_CASE_DIR, USE_CASE_TASK_EXTRACTION_DIR
    global USER_STORY_DIR, FUNCTIONAL_USER_STORY_CLUSTER_SET_PATH
    global NON_FUNCTIONAL_USER_STORY_ANALYSIS_PATH
    global NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR
    global FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR
    
    # Update the model name
    CURRENT_LLM = model_name
    
    # Refresh all path variables that depend on CURRENT_LLM
    USE_CASE_DIR = os.path.join(BASE_DIR, "results", CURRENT_LLM, "use_cases")
    USE_CASE_TASK_EXTRACTION_DIR = os.path.join(BASE_DIR, "results", CURRENT_LLM, "use_case_task_extraction")
    USER_STORY_DIR = os.path.join(BASE_DIR, "results", CURRENT_LLM, "user_stories")
    FUNCTIONAL_USER_STORY_CLUSTER_SET_PATH = os.path.join(BASE_DIR, "results", CURRENT_LLM, "functional_user_story_cluster_set.json")
    NON_FUNCTIONAL_USER_STORY_ANALYSIS_PATH = os.path.join(BASE_DIR, "results", CURRENT_LLM, "non_functional_user_story_analysis.json")
    NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(BASE_DIR, "results", CURRENT_LLM, "conflicts_within_one_group", "non_functional_user_stories")
    FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(BASE_DIR, "results", CURRENT_LLM, "conflicts_within_one_group", "functional_user_stories")
    
    return CURRENT_LLM