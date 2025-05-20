import json
import os
from typing import List, Dict, Optional
from collections import defaultdict

# ==============================================================================================
# USER PERSONA LOADER

#region UserPersona
class UserPersona:
    """Represents a new-format user persona (e.g., Olivia, Elena, Thomas)."""

    def __init__(self, data: dict, no_logging: bool = False):
        self.no_logging = no_logging
        
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
        
        utils = Utils._instance
        if utils is None:
            utils = Utils()

        user_group_keys = utils.load_user_group_keys()
        
        group_summaries = {
            name: utils.load_user_group_description(user_group_keys[name])
            for name in user_group_keys
        }

        group_block = "\n".join(
            f"- {name}: {summary}" for name, summary in group_summaries.items()
        )

        prompt = f"""
You are a classifier for the following system: {utils.load_system_context()}.

Given the following persona information, classify this persona into ONE of these user groups:
{group_block}

Only return the exact group name ({', '.join(user_group_keys.keys())}), nothing else.
Strictly do NOT include any additional text, commentary, or formatting.

Persona:
{json.dumps(minimal_data, indent=2)}
"""
        result = utils.get_llm_response(prompt)

        cleaned = result.strip() if result else "Unknown"

        # Validate against canonical group names
        if cleaned not in user_group_keys:
            if not self.no_logging:
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
    def __init__(self, no_logging: bool = False):
        self.no_logging = no_logging
        self.sample_personas: List[UserPersona] = []
        self.uploaded_personas: List[UserPersona] = []
        self.personas: List[UserPersona] = []

    def load(self):
        utils = Utils._instance
        if utils is None:
            utils = Utils()
            
        self.sample_personas = self._load_personas_from_dir(utils.SAMPLE_PERSONA_DIR)
        self.uploaded_personas = self._load_personas_from_dir(utils.UPLOADED_PERSONA_DIR)

        # Step 1: Ensure filename uniqueness
        sample_files = set(os.listdir(utils.SAMPLE_PERSONA_DIR))
        uploaded_files = set(os.listdir(utils.UPLOADED_PERSONA_DIR))
        conflicts = sample_files.intersection(uploaded_files)
        if conflicts:
            if not self.no_logging:
                print(f"❌ Filename conflicts detected: {conflicts}")
            return

        # Step 2: Load user group definitions
        user_group_keys = utils.load_user_group_keys()
        group_file_count = len(user_group_keys)
        
        if not self.no_logging:
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
                if not self.no_logging:
                    print(f"⚠️ Group '{group_name}' has {len(uploaded)} uploaded personas, using the first two.")
            elif len(uploaded) == 1:
                final_personas.extend(uploaded)
                if not self.no_logging:
                    print(f"⚠️ Group '{group_name}' has only 1 uploaded persona, using it.")
            else:
                final_personas.extend(sample[:2])
                if not self.no_logging:
                    print(f"⚠️ Group '{group_name}' has no uploaded personas, using the first two sample personas.")

        self.personas = final_personas
        if not self.no_logging:
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
                            result.append(UserPersona(data, no_logging=self.no_logging))
                        else:
                            if not self.no_logging:
                                print(f"⚠️ Skipped '{filename}': missing 'Id' or 'Name'.")
                            
                except Exception as e:
                    if not self.no_logging:
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
            return "--".join(pid for pid in sorted(ids))
        except Exception as e:
            if not self.no_logging:
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
            
        if not self.no_logging:
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


# ==============================================================================================
# UTILS SINGLETON CLASS

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("❌ Missing dependency: Please install the OpenAI package using 'pip install openai'.")


class Utils:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Utils, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.CURRENT_LLM = "gpt-4.1-mini"
        self.SYSTEM_NAME = "alfred"

        self.LLM_RESPONSE_LANGUAGE_PROFICIENCY_LEVEL_PATH = os.path.join("data", "llm_response_language_proficiency_level.txt")
        
        self.ROOT_DATA_DIR = os.path.join("data", self.SYSTEM_NAME)

        self.SYSTEM_SUMMARY_PATH = os.path.join(self.ROOT_DATA_DIR, "system_summary.txt")
        self.USER_GROUPS_DIR = os.path.join(self.ROOT_DATA_DIR, "user_groups")
        self.PILLARS_DIR = os.path.join(self.ROOT_DATA_DIR, "pillars")
        self.PERSONA_DIR = os.path.join(self.ROOT_DATA_DIR, "personas")
        self.SAMPLE_PERSONA_DIR = os.path.join(self.PERSONA_DIR, "sample_personas")
        self.UPLOADED_PERSONA_DIR = os.path.join(self.PERSONA_DIR, "uploaded_personas")

        self.USE_CASE_GUIDELINES_PATH = os.path.join(self.ROOT_DATA_DIR, "use_case_rules", "use_case_guidelines.txt")
        self.USE_CASE_TYPE_CONFIG_PATH = os.path.join(self.ROOT_DATA_DIR, "use_case_rules", "use_case_type_config.json")
        self.USE_CASE_TASK_EXTRACTION_EXAMPLE_PATH = os.path.join(self.ROOT_DATA_DIR, "use_case_rules", "use_case_task_extraction_example.txt")

        self.USER_STORY_GUIDELINES_PATH = os.path.join(self.ROOT_DATA_DIR, "user_story_rules", "user_story_guidelines.txt")

        self.FUNCTIONAL_USER_STORY_CLUSTERING_TECHNIQUE_DESCRIPTION_PATH = os.path.join(self.ROOT_DATA_DIR, "user_story_rules", "functional_user_story_clustering_technique_description.txt")

        self.NON_FUNCTIONAL_USER_STORY_CONFLICT_TECHNIQUE_DESCRIPTION_PATH = os.path.join(self.ROOT_DATA_DIR, "user_story_conflict_rules", "non_functional_user_story_conflict_technique_description.txt")
        self.FUNCTIONAL_USER_STORY_CONFLICT_TECHNIQUE_DESCRIPTION_PATH = os.path.join(self.ROOT_DATA_DIR, "user_story_conflict_rules", "functional_user_story_conflict_technique_description.txt")

        # Initialize API client
        self.api_key = self.load_api_key()
        self.client = OpenAI(api_key=self.api_key)

        # Lazy load results path variables that depend on persona abbreviation
        self._init_results_paths()

        self._initialized = True

    def _init_results_paths(self):
        # We must load persona abbreviation dynamically via UserPersonaLoader
        loader = UserPersonaLoader(no_logging=True)
        loader.load()
        persona_abbr = loader.get_persona_abbreviation()

        self.RESULTS_DIR = os.path.join("results")

        self.ROOT_RESULTS_DIR = os.path.join(self.RESULTS_DIR, self.SYSTEM_NAME, persona_abbr, self.CURRENT_LLM)

        self.USE_CASE_DIR = os.path.join(self.ROOT_RESULTS_DIR, "use_cases")
        self.TASK_DIR = os.path.join(self.ROOT_RESULTS_DIR, "tasks")
        self.EXTRACTED_USE_CASE_TASKS_DIR = os.path.join(self.TASK_DIR, "extracted_use_case_tasks")
        self.DUPLICATED_EXTRACTED_USE_CASE_TASKS_DIR = os.path.join(self.TASK_DIR, "duplicated_extracted_use_case_tasks")

        self.USER_STORY_DIR = os.path.join(self.ROOT_RESULTS_DIR, "user_stories")
        self.INVALID_USER_STORY_DIR = os.path.join(self.ROOT_RESULTS_DIR, "invalid_user_stories")
        self.FUNCTIONAL_USER_STORY_CLUSTER_SET_PATH = os.path.join(self.ROOT_RESULTS_DIR, "functional_user_story_cluster_set.json")

        self.CONFLICTS_DIR = os.path.join(self.ROOT_RESULTS_DIR, "user_story_conflicts")

        self.USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(self.CONFLICTS_DIR, "conflicts_within_one_group")
        self.USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR = os.path.join(self.CONFLICTS_DIR, "conflicts_across_two_groups")
        self.INVALID_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(self.CONFLICTS_DIR, "invalid_conflicts_within_one_group")
        self.INVALID_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR = os.path.join(self.CONFLICTS_DIR, "invalid_conflicts_across_two_groups")

        self.NON_FUNCTIONAL_USER_STORY_DECOMPOSITION_PATH = os.path.join(self.ROOT_RESULTS_DIR, "non_functional_user_story_decomposition.json")
        self.NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(self.USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, "non_functional_user_stories")
        self.NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR = os.path.join(self.USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR, "non_functional_user_stories")
        self.INVALID_NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(self.INVALID_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, "non_functional_user_stories")

        self.FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(self.USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, "functional_user_stories")
        self.FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR = os.path.join(self.USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR, "functional_user_stories")
        self.INVALID_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(self.INVALID_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, "functional_user_stories")


    # ===============================
    # Loaders and helpers below...

    def load_llm_response_language_proficiency_level(self) -> str:
        try:
            with open(self.LLM_RESPONSE_LANGUAGE_PROFICIENCY_LEVEL_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Missing LLM response language proficiency level file at: {self.LLM_RESPONSE_LANGUAGE_PROFICIENCY_LEVEL_PATH}")

    def load_pillar_keys(self) -> dict:
        mapping = {}
        for filename in os.listdir(self.PILLARS_DIR):
            if not filename.endswith(".json"):
                continue
            full_path = os.path.join(self.PILLARS_DIR, filename)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    pillar_name = content.get("name")
                    if pillar_name:
                        mapping[pillar_name] = filename
            except Exception as e:
                print(f"⚠️ Failed to parse {filename}: {e}")
        return mapping

    def load_all_pillar_descriptions(self, system_name: Optional[str] = None) -> str:
        if system_name is None:
            system_name = self.SYSTEM_NAME
        filename_map = self.load_pillar_keys()
        functional_pillars = []
        cross_functional = {}

        for name, filename in filename_map.items():
            full_path = os.path.join(self.PILLARS_DIR, filename)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                    pillar_id = obj.get("id", "")
                    desc = obj.get("description", "").strip()
                    if pillar_id in {"Pi-GR", "Pi-DC"}:
                        cross_functional[pillar_id] = f"**{name}**\n{desc}"
                    else:
                        functional_pillars.append((pillar_id, name, desc))
            except Exception as e:
                print(f"⚠️ Failed to parse {filename}: {e}")

        functional_pillars.sort()  
        system_header = f"The {system_name.upper()} system is structured by the following main functional pillars:"
        func_blocks = "\n\n".join([f"**{name}**\n{desc}" for _, name, desc in functional_pillars])

        cross_header = f"\n\nIn addition to these pillars, the {system_name.upper()} system includes two important cross-functional components:"
        cross_blocks = "\n\n".join([cross_functional.get("Pi-GR", ""), cross_functional.get("Pi-DC", "")])

        return f"{system_header}\n\n{func_blocks}\n{cross_header}\n\n{cross_blocks}".strip()

    def load_system_summary(self) -> str:
        try:
            with open(self.SYSTEM_SUMMARY_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Missing ALFRED summary file at: {self.SYSTEM_SUMMARY_PATH}")

    def load_system_context(self, system_name: Optional[str] = None) -> str:
        if system_name is None:
            system_name = self.SYSTEM_NAME
        try:
            with open(self.SYSTEM_SUMMARY_PATH, "r", encoding="utf-8") as f:
                summary = f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Missing ALFRED summary file: {self.SYSTEM_SUMMARY_PATH}")

        pillar_descriptions = self.load_all_pillar_descriptions(system_name)
        
        return f"{summary}\n\n{pillar_descriptions}".strip()

    def load_user_group_keys(self) -> dict:
        keys = {}
        for filename in os.listdir(self.USER_GROUPS_DIR):
            if filename.endswith(".json"):
                file_key = filename.replace(".json", "")
                path = os.path.join(self.USER_GROUPS_DIR, filename)
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

    def get_user_groups(self) -> list:
        return list(self.load_user_group_keys().keys())

    def load_user_group_description(self, group: str) -> str:
        guidelines_files = {
            value: os.path.join(self.USER_GROUPS_DIR, f"{value}.json")
            for value in self.load_user_group_keys().values()
        }

        if group not in guidelines_files:
            raise ValueError(f"❌ Unknown user group: {group}. Valid options are: {', '.join(guidelines_files.keys())}")

        path = guidelines_files[group]

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                user_group_summary = f"Summary: {data['summary']}\n\nNeeds:\n"
                for need in data.get('needs', []):
                    user_group_summary += f"- {need['title']}: {need['description']}\n"
                return user_group_summary
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ User group guideline file not found: {path}")
        except json.JSONDecodeError:
            raise ValueError(f"❌ Error decoding JSON from file: {path}")
        
    def load_all_user_group_descriptions(self) -> str:
        """Loads all user group guidelines based on load_user_group_keys()."""
        guidelines = {}
        for group_label, group_key in self.load_user_group_keys().items():
            try:
                guidelines[group_label] = self.load_user_group_description(group_key)
            except Exception as e:
                print(f"⚠️ Could not load guidelines for '{group_label}' ({group_key}): {e}")
                guidelines[group_label] = "(Missing guidelines)"
        return guidelines

    def load_use_case_guidelines(self) -> str:
        try:
            with open(self.USE_CASE_GUIDELINES_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Missing use-case guideline file at: {self.USE_CASE_GUIDELINES_PATH}")

    def load_use_case_task_example(self) -> str:
        try:
            with open(self.USE_CASE_TASK_EXTRACTION_EXAMPLE_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Missing use-case task analysis file at: {self.USE_CASE_TASK_EXTRACTION_EXAMPLE_PATH}")

    def load_user_story_guidelines(self) -> str:
        try:
            with open(self.USER_STORY_GUIDELINES_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Missing user story summary file at: {self.USER_STORY_GUIDELINES_PATH}")

    def load_non_functional_user_story_clusters_by_each_pillar(self, pillar: str) -> list:
        filename_map = self.load_pillar_keys()
        filename = filename_map.get(pillar)
        if not filename:
            print(f"⚠️ No cluster JSON file mapped for pillar: {pillar}")
            return []

        full_path = os.path.join(self.PILLARS_DIR, filename)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("clustersList", [])
        except FileNotFoundError:
            print(f"❌ Cluster JSON file not found: {full_path}")
            return []
        except json.JSONDecodeError:
            print(f"❌ JSON decode error in cluster file: {full_path}")
            return []
        
    def load_all_non_functional_user_story_clusters(self) -> list:
        """Load and aggregate all non-functional user story clusters across all pillars."""
        cluster_list = []
        filename_map = self.load_pillar_keys()

        for pillar, filename in filename_map.items():
            full_path = os.path.join(self.PILLARS_DIR, filename)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    clusters = data.get("clustersList", [])
                    if clusters:
                        cluster_list.extend(clusters)
            except FileNotFoundError:
                print(f"⚠️ Cluster JSON file not found for pillar '{pillar}': {full_path}")
            except json.JSONDecodeError:
                print(f"❌ JSON decode error in file: {full_path}")
        
        return cluster_list

    def count_all_non_functional_user_story_clusters(self) -> int:
        """Return the total number of non-functional user story clusters across all pillars."""
        all_clusters = self.load_all_non_functional_user_story_clusters()
        return len(all_clusters)

    def load_non_functional_user_story_conflict_technique_description(self) -> str:
        try:
            with open(self.NON_FUNCTIONAL_USER_STORY_CONFLICT_TECHNIQUE_DESCRIPTION_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Missing non-functional user story conflict summary file at: {self.NON_FUNCTIONAL_USER_STORY_CONFLICT_TECHNIQUE_DESCRIPTION_PATH}")

    def load_functional_user_story_conflict_technique_description(self) -> str:
        try:
            with open(self.FUNCTIONAL_USER_STORY_CONFLICT_TECHNIQUE_DESCRIPTION_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Missing non-functional user story conflict summary file at: {self.FUNCTIONAL_USER_STORY_CONFLICT_TECHNIQUE_DESCRIPTION_PATH}")

    def load_functional_user_story_clustering_technique_description(self) -> str:
        try:
            with open(self.FUNCTIONAL_USER_STORY_CLUSTERING_TECHNIQUE_DESCRIPTION_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Missing functional user story clustering technique file at: {self.FUNCTIONAL_USER_STORY_CLUSTERING_TECHNIQUE_DESCRIPTION_PATH}")

    def save_api_key(self, api_key: str, path: str = "api_key.txt") -> bool:
        try:

            with open(path, "w") as f:
                f.write(api_key)
                
            self.api_key = api_key
            
            return True
        except Exception as e:
            print(f"Error saving API key to file: {e}")
            return False

    def load_api_key(self, path: str = "api_key.txt") -> str:
        try:
            with open(path, "r") as file:
                key = file.read().strip()
                if not key:
                    raise ValueError("❌ OpenAI API key file is empty.")
                
                self.api_key = key
                
                return key
        except FileNotFoundError:
            raise FileNotFoundError("❌ API key file not found. Please create 'api_key.txt' and add your API key.")

    def get_openai_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        system_prompt: str = "You are an expert in system requirements engineering."
    ) -> Optional[str]:
        if model is None:
            model = self.CURRENT_LLM
        try:
            response = self.client.responses.create(
                model=model,
                instructions=system_prompt,
                input=prompt,
                temperature=temperature,
            )
            return response.output_text.strip()
        except Exception as e:
            print(f"❌ OpenAI API Error: {e}")
            return None

    def get_llm_response(self, prompt: str) -> Optional[str]:
        if self.CURRENT_LLM.startswith("gpt-4"):
            return self.get_openai_response(prompt, model=self.CURRENT_LLM)
        else:
            raise NotImplementedError(f"❌ LLM '{self.CURRENT_LLM}' is not supported yet.")
