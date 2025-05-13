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

        self.demographic_data: dict = data.get("DemographicData", {})
        self.core_characteristics: List[str] = data.get("CoreCharacteristics", [])
        self.core_goals: List[str] = data.get("CoreGoals", [])
        self.typical_challenges: List[str] = data.get("TypicalChallenges", [])
        self.singularities: List[str] = data.get("Singularities", [])

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
        print(f"   - Work Situation: {self.working_situation}")
        print(f"   - Place of Work: {self.place_of_work}")
        print(f"   - Expertise: {self.expertise}")
        print(f"   - User group: {self.user_group}")


class UserPersonaLoader:
    """Loads user personas from a directory of JSON files."""

    def __init__(self, directory: Optional[str] = None):
        self.directory: str = directory or os.path.join("data", "personas")
        self.personas: List[UserPersona] = []

    def load(self) -> None:
        try:
            for filename in os.listdir(self.directory):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.directory, filename)
                    with open(filepath, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        if "Id" in data and "Name" in data:
                            self.personas.append(UserPersona(data))
                        else:
                            print(f"⚠️ Skipping '{filename}': missing 'Id' or 'Name'.")
            print(f"✅ Loaded {len(self.personas)} persona(s) successfully.")
        except Exception as e:
            print(f"❌ Error loading personas: {e}")

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