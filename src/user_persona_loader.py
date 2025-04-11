import json
import os
from typing import List, Optional
from utils import get_llm_response, load_alfred_summary, load_user_group_summary


class UserPersona:
    """Represents a new-format user persona (e.g., Olivia, Elena, Thomas)."""

    def __init__(self, data: dict):
        self.raw_data = data
        self.id: str = data.get("Id", "Unknown")
        self.name: str = data.get("Name", "Unknown")
        self.role: str = data.get("Role", "Unknown")
        self.tagline: str = data.get("Tagline", "")

        self.demographic_data: dict = data.get("Demographic data", {})
        self.core_characteristics: List[str] = data.get("Core characteristics", [])
        self.core_goals: List[str] = data.get("Core goals", [])
        self.typical_challenges: List[str] = data.get("Typical challenges", [])
        self.singularities: List[str] = data.get("Singularities", [])

        self.working_situation: str = data.get("Working situation", "")
        self.place_of_work: str = data.get("Place of work", "")
        self.expertise: str = data.get("Expertise", "")

        self.main_tasks: List[str] = data.get("Main tasks with system support", [])
        self.most_important_tasks: List[str] = data.get("Most important tasks", [])
        self.least_important_tasks: List[str] = data.get("Least important tasks", [])
        self.miscellaneous: List[str] = data.get("Miscellaneous", [])
        
    def classify_user_group(self) -> str:
        """Use LLM to classify this persona into one of the 3 user groups."""
        minimal_data = {
            "Role": self.role,
            "Core goals": self.core_goals,
            "Typical challenges": self.typical_challenges,
            "Working situation": self.working_situation,
            "Expertise": self.expertise,
            "Main tasks with system support": self.main_tasks,
        }

        prompt = f"""
You are a classifier for the ALFRED system: {load_alfred_summary()}.

Given the following persona information, classify this persona into ONE of these user groups:
- Older Adults: {load_user_group_summary("older_adults")}
- Caregivers and Medical Staff: {load_user_group_summary("caregivers_and_medical_staff")}
- Developers and App Creators: {load_user_group_summary("developers_and_app_creators")}

Only return the exact group name (either "Older Adults", "Caregivers and Medical Staff", or "Developers and App Creators"), nothing else.
Strictly do NOT include any additional text, commentary, or formatting.

Persona:
{json.dumps(minimal_data, indent=2)}
"""
        result = get_llm_response(prompt)
        return result.strip() if result else "Unknown"

    def __repr__(self):
        return f"UserPersona(Name={self.name})"
    
    def to_dict(self) -> dict:
        return {
            "Id": self.id,
            "Name": self.name,
            "Role": self.role,
            "Tagline": self.tagline,
            "Demographic data": self.demographic_data,
            "Core goals": self.core_goals,
            "Typical challenges": self.typical_challenges,
            "Singularities": self.singularities,
            "Working situation": self.working_situation,
            "Place of work": self.place_of_work,
            "Expertise": self.expertise,
            "Main tasks with system support": self.main_tasks,
            "Most important tasks": self.most_important_tasks,
            "Least important tasks": self.least_important_tasks,
            "Miscellaneous": self.miscellaneous
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
        print(f"   - Work Situation: {self.working_situation}")
        print(f"   - Place of Work: {self.place_of_work}")
        print(f"   - Expertise: {self.expertise}")
        print(f"   - Main Tasks: {', '.join(self.main_tasks)}")
        print(f"   - Most Important Tasks: {', '.join(self.most_important_tasks)}")
        print(f"   - Least Important Tasks: {', '.join(self.least_important_tasks)}")
        print(f"   - Miscellaneous: {', '.join(self.miscellaneous)}")


class UserPersonaLoader:
    """Loads new-format user personas from a directory of JSON files."""

    def __init__(self, directory: Optional[str] = None):
        self.directory: str = directory or os.path.join("data", "personas")
        self.personas: List[UserPersona] = []

    def load(self) -> None:
        """Loads all valid JSON files in the directory into UserPersona instances."""
        try:
            for filename in os.listdir(self.directory):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.directory, filename)
                    with open(filepath, "r", encoding="utf-8") as file:
                        data = json.load(file)

                        # Validate minimum required fields
                        if "Id" in data and "Name" in data:
                            self.personas.append(UserPersona(data))
                        else:
                            print(f"⚠️ Skipping '{filename}': missing 'Id' or 'Name'.")
            print(f"✅ Loaded {len(self.personas)} persona(s) successfully.")
        except Exception as e:
            print(f"❌ Error loading personas: {e}")

    def get_personas(self) -> List[UserPersona]:
        """Returns all loaded personas."""
        return self.personas

    def print_persona(self, name: str) -> None:
        """Prints details of a persona by name."""
        for persona in self.personas:
            if persona.name.lower() == name.lower():
                persona.display()
                return
        print(f"❌ Persona with name '{name}' not found.")

    def print_all_personas(self) -> None:
        """Prints all loaded personas."""
        if not self.personas:
            print("❌ No personas loaded.")
            return
        for persona in self.personas:
            persona.display()
        print()

    def find_by_role(self, role: str) -> List[UserPersona]:
        """Returns personas matching a given role."""
        return [p for p in self.personas if p.role.lower() == role.lower()]
