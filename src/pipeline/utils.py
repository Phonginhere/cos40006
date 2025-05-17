import json
import os

from typing import List, Dict, Optional
from collections import defaultdict

# ===============================================================================================
# GENRAL CONSTANTS 

# Global variable to specify which LLM is being used in the pipeline
# CURRENT_LLM = "gpt-4o-mini"
CURRENT_LLM = "gpt-4.1-mini"

SYSTEM_NAME = "alfred"

# ==============================================================================================
# DATA PATH CONSTANTS 
ROOT_DATA_DIR = os.path.join("data", SYSTEM_NAME)

SYSTEM_SUMMARY_PATH = os.path.join(ROOT_DATA_DIR, "system_summary.txt")
USER_GROUP_GUIDELINES_DIR = os.path.join(ROOT_DATA_DIR, "user_group_guidelines")
PERSONA_DIR = os.path.join(ROOT_DATA_DIR, "personas")
SAMPLE_PERSONA_DIR = os.path.join(PERSONA_DIR, "sample_personas")
UPLOADED_PERSONA_DIR = os.path.join(PERSONA_DIR, "uploaded_personas")

USE_CASE_GUIDELINES_PATH = os.path.join(ROOT_DATA_DIR, "use_case_rules", "use_case_guidelines.txt")
USE_CASE_TYPE_CONFIG_PATH = os.path.join(ROOT_DATA_DIR, "use_case_rules", "use_case_type_config.json")
USE_CASE_TASK_EXTRACTION_EXAMPLE_PATH = os.path.join(ROOT_DATA_DIR, "use_case_rules", "use_case_task_extraction_example.txt")

USER_STORY_GUIDELINES_PATH = os.path.join(ROOT_DATA_DIR, "user_story_rules", "user_story_guidelines.txt")

PILLAR_CLUSTERING_SUMMARY_DIR = os.path.join(ROOT_DATA_DIR, "pillar_clustering_summary")
FUNCTIONAL_USER_STORY_CLUSTERING_TECHNIQUE_GUIDELINES = os.path.join(ROOT_DATA_DIR, "user_story_rules", "functional_user_story_clustering_technique_guidelines.txt")

NON_FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH = os.path.join(ROOT_DATA_DIR, "user_story_conflict_rules", "non_functional_user_story_conflict_summary.txt")
FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH = os.path.join(ROOT_DATA_DIR, "user_story_conflict_rules", "functional_user_story_conflict_summary.txt")

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

def load_user_group_keys() -> dict:
    """
    Dynamically reads all JSON files in USER_GROUP_GUIDELINES_DIR and constructs a dict:
    { group_name (from 'name' field): file_key (e.g., user_group_1) }
    """
    keys = {}
    for filename in os.listdir(USER_GROUP_GUIDELINES_DIR):
        if filename.endswith(".json"):
            file_key = filename.replace("_guidelines.json", "")
            path = os.path.join(USER_GROUP_GUIDELINES_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    group_name = data.get("name")
                    if group_name:
                        keys[group_name] = file_key
                    else:
                        print(f"⚠️ Skipping {filename}: missing 'name' field.")
            except Exception as e:
                print(f"❌ Error reading user group file {filename}: {e}")
    return keys


def get_user_groups() -> list:
    """
    Returns a list of user group names, derived from the keys in USER_GROUP_GUIDELINES_DIR.
    """
    return list(load_user_group_keys().keys())

def load_user_group_guidelines(group: str) -> str:
    """Loads the user group guidelines from a JSON file based on the user group."""
    guidelines_files = {
        value: os.path.join(USER_GROUP_GUIDELINES_DIR, f"{value}_guidelines.json")
        for value in load_user_group_keys().values()
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
    """Loads all user group guidelines based on load_user_group_keys()."""
    guidelines = {}
    for group_label, group_key in load_user_group_keys().items():
        try:
            guidelines[group_label] = load_user_group_guidelines(group_key)
        except Exception as e:
            print(f"⚠️ Could not load guidelines for '{group_label}' ({group_key}): {e}")
            guidelines[group_label] = "(Missing guidelines)"
    return guidelines
    
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
    
# ==================================================================================================
# USER PERSONA LOADER

#region UserPersona
class UserPersona:
    """Represents a new-format user persona (e.g., Olivia, Elena, Thomas)."""

    def __init__(self, data: dict):
        self.raw_data = data
        self.id: str = data.get("Id", "Unknown")
        self.name: str = data.get("Name", "Unknown")
        self.role: str = data.get("Role", "Unknown")
        self.tagline: str = data.get("Tagline", "")

        self.demographic_data: dict = data.get("DemographicData", {})
        self.core_characteristics: List[str] = data.get("CoreCharacteristics", [])
        self.core_goals: List[str] = data.get("CoreGoals", [])
        self.typical_challenges: List[str] = data.get("TypicalChallenges", [])
        self.singularities: List[str] = data.get("Singularities", [])
        self.main_actions: List[str] = data.get("MainActions", [])

        self.working_situation: str = data.get("WorkingSituation", "")
        self.place_of_work: str = data.get("PlaceOfWork", "")
        self.expertise: str = data.get("Expertise", "")
        
        # Set user group once
        self.user_group = self.classify_user_group()
        
    def classify_user_group(self) -> str:
        """Use LLM to classify this persona into one of the 3 user groups."""
        minimal_data = {
            "Role": self.role,
            "CoreGoals": self.core_goals,
            "TypicalChallenges": self.typical_challenges,
            "WorkingSituation": self.working_situation,
            "Expertise": self.expertise,
        }
        
        user_group_keys = load_user_group_keys()
        
        group_summaries = {
            name: load_user_group_guidelines(user_group_keys[name])
            for name in user_group_keys
        }

        group_block = "\n".join(
            f"- {name}: {summary}" for name, summary in group_summaries.items()
        )

        prompt = f"""
You are a classifier for the following system: {load_system_summary()}.

Given the following persona information, classify this persona into ONE of these user groups:
{group_block}

Only return the exact group name ({', '.join(user_group_keys.keys())}), nothing else.
Strictly do NOT include any additional text, commentary, or formatting.

Persona:
{json.dumps(minimal_data, indent=2)}
"""
        result = get_llm_response(prompt)

        cleaned = result.strip() if result else "Unknown"

        # Validate against canonical group names
        if cleaned not in user_group_keys:
            print(f"⚠️ LLM returned unknown group '{cleaned}' for persona {self.name}.")
            return "Unknown"

        return cleaned

    def __repr__(self):
        return f"UserPersona(Name={self.name})"
    
    def to_prompt_string(self) -> str:
        return json.dumps({
            "Id": self.id,
            "Name": self.name,
            "Role": self.role,
            "UserGroup": self.user_group,
            "Tagline": self.tagline,
            "DemographicData": self.demographic_data,
            "CoreGoals": self.core_goals,
            "TypicalChallenges": self.typical_challenges,
            "Singularities": self.singularities,
            "MainActions": self.main_actions,
            "WorkingSituation": self.working_situation,
            "PlaceOfWork": self.place_of_work,
            "Expertise": self.expertise,
        }, indent=2)

    def to_dict(self) -> dict:
        return {
            "Id": self.id,
            "Name": self.name,
            "Role": self.role,
            "Tagline": self.tagline,
            "DemographicData": self.demographic_data,
            "CoreGoals": self.core_goals,
            "TypicalChallenges": self.typical_challenges,
            "Singularities": self.singularities,
            "MainActions": self.main_actions,
            "WorkingSituation": self.working_situation,
            "PlaceOfWork": self.place_of_work,
            "Expertise": self.expertise,
        }

    def display(self):
        print(f"\n👤 Persona: {self.name} (ID: {self.id})")
        print(f"   - Role: {self.role}")
        print(f"   - Tagline: {self.tagline}")
        print(f"   - Demographics: {self.demographic_data}")
        print(f"   - Core Characteristics: {', '.join(self.core_characteristics)}")
        print(f"   - Core Goals: {', '.join(self.core_goals)}")
        print(f"   - Challenges: {', '.join(self.typical_challenges)}")
        print(f"   - Singularities: {', '.join(self.singularities)}")
        print(f"   - Main actions: {', '.join(self.main_actions)}")
        print(f"   - Work Situation: {self.working_situation}")
        print(f"   - Place of Work: {self.place_of_work}")
        print(f"   - Expertise: {self.expertise}")
        print(f"   - User group: {self.user_group}")


class UserPersonaLoader:
    def __init__(self):
        self.sample_personas: List[UserPersona] = []
        self.uploaded_personas: List[UserPersona] = []
        self.personas: List[UserPersona] = []

    def load(self):
        self.sample_personas = self._load_personas_from_dir(SAMPLE_PERSONA_DIR)
        self.uploaded_personas = self._load_personas_from_dir(UPLOADED_PERSONA_DIR)

        # Step 1: Ensure filename uniqueness
        sample_files = set(os.listdir(SAMPLE_PERSONA_DIR))
        uploaded_files = set(os.listdir(UPLOADED_PERSONA_DIR))
        conflicts = sample_files.intersection(uploaded_files)
        if conflicts:
            print(f"❌ Filename conflicts detected: {conflicts}")
            return

        # Step 2: Load user group definitions
        user_group_keys = load_user_group_keys()
        group_file_count = len(user_group_keys)
        print(f"📊 Detected {group_file_count} user groups from guidelines.")

        # Step 3: Categorize personas by group
        uploaded_by_group = defaultdict(list)
        for persona in self.uploaded_personas:
            uploaded_by_group[persona.user_group].append(persona)

        sample_by_group = defaultdict(list)
        for persona in self.sample_personas:
            sample_by_group[persona.user_group].append(persona)

        # Step 4: Select final personas for each group
        final_personas = []
        for group_name in user_group_keys:
            uploaded = uploaded_by_group.get(group_name, [])
            sample = sample_by_group.get(group_name, [])

            if len(uploaded) >= 2:
                final_personas.extend(uploaded[:2])
                print(f"⚠️ Group '{group_name}' has {len(uploaded)} uploaded personas, using the first two.")
            elif len(uploaded) == 1:
                final_personas.extend(uploaded)
                print(f"⚠️ Group '{group_name}' has only 1 uploaded persona, using it.")
            else:
                final_personas.extend(sample[:2])
                print(f"⚠️ Group '{group_name}' has no uploaded personas, using the first two sample personas.")

        self.personas = final_personas
        print(f"✅ Final persona set includes {len(self.personas)} personas from {group_file_count} groups.")

    def _load_personas_from_dir(self, directory: str) -> List['UserPersona']:
        result = []
        for filename in os.listdir(directory):
            if filename.endswith(".json"):
                path = os.path.join(directory, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "Id" in data and "Name" in data:
                            result.append(UserPersona(data))
                        else:
                            print(f"⚠️ Skipped '{filename}': missing 'Id' or 'Name'.")
                except Exception as e:
                    print(f"❌ Failed to read '{filename}': {e}")
        return result

    def get_persona_abbreviation(self) -> str:
        """
        Returns a short abbreviation string like 'P001-P002-P004'
        based only on the final selected personas.
        Requires `load()` to have been called first.
        """
        try:
            ids = [p.id for p in self.personas]
            return "-".join(pid.replace("P-", "P") for pid in sorted(ids))
        except Exception as e:
            print(f"⚠️ Could not generate persona abbreviation: {e}")
            return "UnknownPersonas"

    def get_persona_ids(self) -> List[str]:
        """
        Returns a list of persona IDs from the final loaded set.
        """
        return sorted(p.id for p in self.personas)

    def get_personas(self) -> List[UserPersona]:
        return self.personas

    def print_persona(self, name: str) -> None:
        for persona in self.personas:
            if persona.name.lower() == name.lower():
                persona.display()
                return
        print(f"❌ Persona with name '{name}' not found.")

    def print_all_personas(self) -> None:
        if not self.personas:
            print("❌ No personas loaded.")
            return
        for persona in self.personas:
            persona.display()
        print()

    def find_by_role(self, role: str) -> List[UserPersona]:
        return [p for p in self.personas if p.role.lower() == role.lower()]
#endregion

def get_persona_abbreviation() -> str:
    """
    Returns a short abbreviation string based on the final selected personas,
    by creating a local instance of UserPersonaLoader (without global sharing).
    This is used for constructing paths like ROOT_RESULTS_DIR.
    """
    try:       
        loader = UserPersonaLoader()
        loader.load()
        return loader.get_persona_abbreviation()

    except Exception as e:
        print(f"⚠️ Could not generate persona abbreviation: {e}")
        return "UnknownPersonas"
    
# ==================================================================================================
# RESULTS PATH CONSTANTS
ROOT_RESULTS_DIR = os.path.join("results", SYSTEM_NAME, get_persona_abbreviation(), CURRENT_LLM) 

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
