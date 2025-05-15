import json
import os
from typing import List, Optional

from pipeline.utils import CURRENT_LLM, USE_CASE_DIR, USE_CASE_TYPE_CONFIG_PATH


class UseCase:
    """Represents a single ALFRED system use case."""

    def __init__(self, data: dict):
        if "id" not in data or "personas" not in data:
            raise ValueError("❌ A use case must contain 'id' and 'personas'.")

        self.id: str = data["id"]
        self.personas: List[str] = data["personas"]

        self.use_case_type: str = data.get("useCaseType", "")
        self.user_groups: List[str] = data.get("userGroups", [])
        self.pillars: List[str] = data.get("pillars", [])
        
        self.name: str = data.get("name", "")
        self.description: str = data.get("description", "")
        self.scenario: Optional[str] = data.get("scenario", None)

    def __repr__(self):
        return f"UseCase(id={self.id}, name={self.name})"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "useCaseType": self.use_case_type,
            "userGroups": self.user_groups,
            "pillars": self.pillars,
            "name": self.name,
            "description": self.description,
            "scenario": self.scenario,
            "personas": self.personas
        }


class UseCaseLoader:
    """Loads all ALFRED use cases from a directory of JSON files."""

    def __init__(self, directory: str = USE_CASE_DIR):
        self.directory = directory
        self.use_cases: List[UseCase] = []

    def load(self) -> None:
        if not os.path.exists(self.directory):
            print(f"❌ Use case directory not found: {self.directory}")
            return

        try:
            count = 0
            self.use_cases = []
            
            for filename in os.listdir(self.directory):
                if filename.startswith("UC-") and filename.endswith(".json"):
                    full_path = os.path.join(self.directory, filename)
                    with open(full_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.use_cases.append(UseCase(data))
                        count += 1
            print(f"✅ Loaded {count} use case(s) from {self.directory}")
        except Exception as e:
            print(f"❌ Failed to load use cases: {e}")

    def get_all(self) -> List[UseCase]:
        return self.use_cases

    def save_all(self) -> None:
        os.makedirs(self.directory, exist_ok=True)
        for use_case in self.use_cases:
            file_path = os.path.join(self.directory, f"{use_case.id}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(use_case.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"💾 Saved {len(self.use_cases)} use case files to {self.directory}")

    def print_all_use_cases(self) -> None:
        if not self.use_cases:
            print("❌ No use cases loaded.")
            return

        for uc in self.use_cases:
            print(f"\n🧾 {uc.id} - {uc.name}")
            print(f"   Type: {uc.use_case_type}")
            print(f"   User Groups: {', '.join(uc.user_groups)}")
            print(f"   Pillars: {', '.join(uc.pillars)}")
            print(f"   Description: {uc.description}")
            
            if isinstance(uc.personas, list) and uc.personas:
                print(f"   Personas: {', '.join(uc.personas)}")
            else:
                print("   Personas: None")

            if isinstance(uc.scenario, str) and uc.scenario.strip():
                preview = uc.scenario.strip().replace('\n', ' ')[:150]
                print(f"   Scenario: {preview}{'...' if len(uc.scenario) > 150 else ''}")
            else:
                print("   Scenario: None")
        print()
        
        
def load_use_case_type_config():
    """Load the use case type configuration (distribution + constraints)."""
    if not os.path.exists(USE_CASE_TYPE_CONFIG_PATH):
        raise FileNotFoundError(f"Use case type config not found at: {USE_CASE_TYPE_CONFIG_PATH}")

    with open(USE_CASE_TYPE_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    print(f"✅ Loaded {len(config)} use case type configuration entries.")
    return config