import json
import os
from typing import List, Dict

# ==================================================================================================
# ALFRED SYSTEM SUMMARY LOADER

def load_alfred_summary(path: str = "data/alfred_summary.txt") -> str:
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
        "older_adults": "data/older_adults_summary.json",
        "caregivers_and_medical_staff": "data/caregivers_and_medical_staff_summary.json",
        "developers_and_app_creators": "data/developers_and_app_creators_summary.json"
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
# LLM HANDLER

# Global variable to specify which LLM is being used in the pipeline
CURRENT_LLM = "gpt-4o-mini"

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
    max_tokens: int = 8192,
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
def get_llm_response(prompt: str) -> str:
    """Dispatches LLM call based on the currently selected model."""
    if CURRENT_LLM.startswith("gpt-4"):
        return get_openai_response(prompt, model=CURRENT_LLM)
    else:
        raise NotImplementedError(f"❌ LLM '{CURRENT_LLM}' is not supported yet.")
