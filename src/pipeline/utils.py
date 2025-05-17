import json
import os

from typing import List, Dict, Optional

# ==================================================================================================
# PERSONA ABBREVIATION LOADER
def load_persona_ids_only() -> List[str]:
    """Returns a sorted list of persona IDs from the persona JSON files without fully loading the objects."""
    ids = []
    try:
        for filename in os.listdir(PERSONA_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(PERSONA_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    if "Id" in data:
                        ids.append(data["Id"])
    except Exception as e:
        print(f"❌ Error reading persona IDs: {e}")
    return sorted(ids)

def get_persona_abbreviation() -> str:
    """Returns a short abbreviation string from persona IDs like 'P001-P002-P004'."""
    try:
        persona_ids = load_persona_ids_only()
        return "-".join(pid.replace("P-", "P") for pid in persona_ids)
    except Exception as e:
        print(f"⚠️ Could not generate persona abbreviation: {e}")
        return "UnknownPersonas"

# ===============================================================================================
# CONSTANTS

# Global variable to specify which LLM is being used in the pipeline
# CURRENT_LLM = "gpt-4o-mini"
CURRENT_LLM = "gpt-4.1-mini"

SYSTEM_NAME = "alfred"

USER_GROUP_KEYS = {
    "Developers and App Creators": "user_group_1",
    "Caregivers and Medical Staff": "user_group_2",
    "Older Adults": "user_group_3",
}

USER_GROUPS = list(USER_GROUP_KEYS.keys())

ROOT_DATA_DIR = os.path.join("data", SYSTEM_NAME)

SYSTEM_SUMMARY_PATH = os.path.join(ROOT_DATA_DIR, "system_summary.txt")
USER_GROUP_GUIDELINES_DIR = os.path.join(ROOT_DATA_DIR, "user_group_guidelines")
PERSONA_DIR = os.path.join(ROOT_DATA_DIR, "personas")

USE_CASE_GUIDELINES_PATH = os.path.join(ROOT_DATA_DIR, "use_case_rules", "use_case_guidelines.txt")
USE_CASE_TYPE_CONFIG_PATH = os.path.join(ROOT_DATA_DIR, "use_case_rules", "use_case_type_config.json")
USE_CASE_TASK_EXTRACTION_EXAMPLE_PATH = os.path.join(ROOT_DATA_DIR, "use_case_rules", "use_case_task_extraction_example.txt")

USER_STORY_GUIDELINES_PATH = os.path.join(ROOT_DATA_DIR, "user_story_rules", "user_story_guidelines.txt")

PILLAR_CLUSTERING_SUMMARY_DIR = os.path.join(ROOT_DATA_DIR, "pillar_clustering_summary")
FUNCTIONAL_USER_STORY_CLUSTERING_TECHNIQUE_GUIDELINES = os.path.join(ROOT_DATA_DIR, "user_story_rules", "functional_user_story_clustering_technique_guidelines.txt")

NON_FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH = os.path.join(ROOT_DATA_DIR, "user_story_conflict_rules", "non_functional_user_story_conflict_summary.txt")
FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH = os.path.join(ROOT_DATA_DIR, "user_story_conflict_rules", "functional_user_story_conflict_summary.txt")

ROOT_RESULTS_DIR = os.path.join("results", get_persona_abbreviation(), CURRENT_LLM) 

USE_CASE_DIR = os.path.join(ROOT_RESULTS_DIR, "use_cases")
USE_CASE_TASK_EXTRACTION_DIR = os.path.join(ROOT_RESULTS_DIR, "use_case_task_extraction")

USER_STORY_DIR = os.path.join(ROOT_RESULTS_DIR, "user_stories")
FUNCTIONAL_USER_STORY_CLUSTER_SET_PATH = os.path.join(ROOT_RESULTS_DIR, "functional_user_story_cluster_set.json")

USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(ROOT_RESULTS_DIR, "conflicts_within_one_group")
USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR = os.path.join(ROOT_RESULTS_DIR, "conflicts_across_two_groups")

NON_FUNCTIONAL_USER_STORY_DECOMPOSITION_PATH = os.path.join(ROOT_RESULTS_DIR, "non_functional_user_story_decomposition.json")
NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, "non_functional_user_stories")
NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR = os.path.join(USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR, "non_functional_user_stories")

FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, "functional_user_stories")
FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR = os.path.join(USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR, "functional_user_stories")

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
# USER GROUP GUIDELINES LOADER
def load_user_group_guidelines(group: str) -> str:
    """Loads the user group guidelines from a JSON file based on the user group."""
    guidelines_files = {
        value: os.path.join(USER_GROUP_GUIDELINES_DIR, f"{value}_guidelines.json")
        for value in USER_GROUP_KEYS.values()
    }

    if group not in guidelines_files:
        raise ValueError(f"❌ Unknown user group: {group}. Valid options are: {', '.join(guidelines_files.keys())}")

    path = guidelines_files[group]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Create a formatted string that includes both summary and needs
            user_group_summary = f"Summary: {data['summary']}\n\nNeeds:\n"
            for need in data.get('needs', []):
                user_group_summary += f"- {need['title']}: {need['description']}\n"
            return user_group_summary
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ User group guideline file not found: {path}")
    except json.JSONDecodeError:
        raise ValueError(f"❌ Error decoding JSON from file: {path}")
    
def load_all_user_group_guidelines() -> Dict[str, str]:
    """Loads all user group guidelines based on USER_GROUP_KEYS."""
    guidelines = {}
    for group_label, group_key in USER_GROUP_KEYS.items():
        try:
            guidelines[group_label] = load_user_group_guidelines(group_key)
        except Exception as e:
            print(f"⚠️ Could not load guidelines for '{group_label}' ({group_key}): {e}")
            guidelines[group_label] = "(Missing guidelines)"
    return guidelines

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
def load_use_case_guidelines() -> str:
    try:
        with open(USE_CASE_GUIDELINES_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing use-case guideline file at: {USE_CASE_GUIDELINES_PATH}")
    
def load_use_case_task_example() -> str:
    try:
        with open(USE_CASE_TASK_EXTRACTION_EXAMPLE_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing use-case task analysis file at: {USE_CASE_TASK_EXTRACTION_EXAMPLE_PATH}")
    
# ==================================================================================================
# USER STORY GUIDELINES LOADER
def load_user_story_guidelines() -> str:
    try:
        with open(USER_STORY_GUIDELINES_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing user story summary file at: {USER_STORY_GUIDELINES_PATH}")

# ==================================================================================================
# NON-FUNCTIONAL USER STORY CLUSTER SUMMARY LOADER

def load_non_functional_user_story_cluster_summary(pillar: str) -> list:
    """Load non-functional user story clusters as JSON objects for the given pillar."""
    filename_map = {
        "General Requirements": "general_requirements_clusters_summary.json",
        "Pillar 1 - User-Driven Interaction Assistant": "pillar_1_clusters_summary.json",
        "Pillar 2 - Personalized Social Inclusion": "pillar_2_clusters_summary.json",
        "Pillar 3 - Effective & Personalized Care": "pillar_3_clusters_summary.json",
        "Pillar 4 - Physical & Cognitive Impairments Prevention": "pillar_4_clusters_summary.json",
        "Developer Core": "developer_core_clusters_summary.json"
    }
    filename = filename_map.get(pillar)
    if not filename:
        print(f"⚠️ No cluster JSON file mapped for pillar: {pillar}")
        return []

    full_path = os.path.join(PILLAR_CLUSTERING_SUMMARY_DIR, filename)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Cluster JSON file not found: {full_path}")
        return []
    except json.JSONDecodeError:
        print(f"❌ JSON decode error in cluster file: {full_path}")
        return []
    
# ==================================================================================================
# NON-FUNCTIONAL USER STORY CONFLICT SUMMARY LOADER
def load_non_functional_user_story_conflict_summary() -> str:
    try:
        with open(NON_FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing non-functional user story conflict summary file at: {NON_FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH}")
    
def load_functional_user_story_conflict_summary() -> str:
    try:
        with open(FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing non-functional user story conflict summary file at: {FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH}")

def load_functional_user_story_clustering_technique() -> str:
    try:
        with open(FUNCTIONAL_USER_STORY_CLUSTERING_TECHNIQUE_GUIDELINES, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing functional user story clustering technique file at: {FUNCTIONAL_USER_STORY_CLUSTERING_TECHNIQUE_GUIDELINES}")

# ==================================================================================================
# LLM HANDLER

# Try to import OpenAI
try:
    from openai import OpenAI
except ImportError:
    raise ImportError("❌ Missing dependency: Please install the OpenAI package using 'pip install openai'.")

# Load OpenAI API key from file
def load_api_key(path: str = "api_key.txt") -> str:
    """Loads the OpenAI API key from a separate text file."""
    try:
        with open(path, "r") as file:
            key = file.read().strip()
            if not key:
                raise ValueError("❌ OpenAI API key file is empty.")
            return key
    except FileNotFoundError:
        raise FileNotFoundError("❌ API key file not found. Please create 'api_key.txt' and add your API key.")

# Set OpenAI API key
api_key = load_api_key()
client = OpenAI(api_key=api_key)

# Generate a response using the Responses API
def get_openai_response(
    prompt: str,
    model: str = CURRENT_LLM,
    temperature: float = 0.7,
    system_prompt: str = "You are an expert in system requirements engineering."
) -> str:
    """Uses OpenAI's Responses API to generate a response from the specified model."""
    try:
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
        return None

# LLM Dispatcher
def get_llm_response(prompt: str) -> str:
    """Dispatches LLM call based on the currently selected model."""
    if CURRENT_LLM.startswith("gpt-4"):
        return get_openai_response(prompt, model=CURRENT_LLM)
    else:
        raise NotImplementedError(f"❌ LLM '{CURRENT_LLM}' is not supported yet.")
