import json
import os
from typing import List, Dict

# ===============================================================================================
# CONSTANTS

# Global variable to specify which LLM is being used in the pipeline
CURRENT_LLM = "gpt-4o-mini"

PILLAR_KEYS = [
    ("Pillar 1 - User-Driven Interaction Assistant", "pillar_1_user_stories.json"),
    ("Pillar 2 - Personalized Social Inclusion", "pillar_2_user_stories.json"),
    ("Pillar 3 - Effective & Personalized Care", "pillar_3_user_stories.json"),
    ("Pillar 4 - Physical & Cognitive Impairments Prevention", "pillar_4_user_stories.json"),
    ("General Requirements", "general_user_stories.json"),
]
PILLARS = [item[0] for item in PILLAR_KEYS]

USER_GROUP_KEYS = {
    "Older Adults": "older_adults",
    "Caregivers and Medical Staff": "caregivers_and_medical_staff",
    "Developers and App Creators": "developers_and_app_creators"
}

USER_GROUPS = list(USER_GROUP_KEYS.keys())

USE_CASE_DIR = os.path.join("results", CURRENT_LLM, "use_cases")
USE_CASE_TYPE_CONFIG_PATH = os.path.join("data", "use_case_rules", "use_case_type_config.json")
USE_CASE_TASK_DIR = os.path.join("results", CURRENT_LLM, "use_case_task_analysis")
FINAL_USER_STORY_DIR = os.path.join("results", CURRENT_LLM, "user_stories")

# ==================================================================================================
# ALFRED SYSTEM SUMMARY LOADER

def load_alfred_summary(path: str = "data/alfred_system_summaries/alfred_system_summary.txt") -> str:
    """Loads the ALFRED system summary from a plain text file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing ALFRED summary file: {path}")
    
# ==================================================================================================
# USER GROUP SUMMARY LOADER

def load_user_group_summary(group: str) -> str:
    """Loads the user group summary from a JSON file based on the user group (older adults, caregivers, developers)."""
    summary_files = {
        value: f"data/alfred_system_summaries/{value}_summary.json"
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
    
# ==================================================================================================
# USE CASE SUMMARY LOADER
def load_use_case_summary(path: str = "data/use_case_rules/use_case_summary.txt") -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing use-case summary file at: {path}")
    
def load_use_case_task_example(path: str = "data/use_case_rules/use_case_task_analysis_example.txt") -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing use-case task analysis file at: {path}")


# ==================================================================================================
# LLM HANDLER

# Try to import OpenAI
try:
    import openai
except ImportError:
    raise ImportError("❌ Missing dependency: Please install the OpenAI package using 'pip install openai'.")

# Load OpenAI API key from file
def load_api_key(path: str = "openai_api_key.txt") -> str:
    """Loads the OpenAI API key from a separate text file."""
    try:
        with open(path, "r") as file:
            key = file.read().strip()
            if not key:
                raise ValueError("❌ OpenAI API key file is empty.")
            return key
    except FileNotFoundError:
        raise FileNotFoundError("❌ API key file not found. Please create 'openai_api_key.txt' and add your API key.")

# Set OpenAI API key
openai.api_key = load_api_key()

# Generate a response using OpenAI
def get_openai_response(
    prompt: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 16384,
    system_prompt: str = "You are an expert in system requirements engineering."
) -> str:
    """Uses OpenAI's API to generate a response from the specified model."""
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            n=1
        )
        return response.choices[0].message.content.strip()
    
    except openai.OpenAIError as e:
        print(f"❌ OpenAI API Error: {e}")
        return None

# LLM Dispatcher
def get_llm_response(prompt: str, max_tokens: int = 16384) -> str:
    """Dispatches LLM call based on the currently selected model."""
    if CURRENT_LLM.startswith("gpt-4"):
        return get_openai_response(prompt, model=CURRENT_LLM, max_tokens=max_tokens)
    else:
        raise NotImplementedError(f"❌ LLM '{CURRENT_LLM}' is not supported yet.")
