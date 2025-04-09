import json
import os
from typing import List, Dict, Optional
from utils import CURRENT_LLM

# Paths
OUTPUT_FILE = os.path.join("results", CURRENT_LLM, "raw_requirements.json")

class RawRequirementLoader:
    def __init__(self, path: str = OUTPUT_FILE):
        self.path = path
        self.requirements: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ File not found: {self.path}")
            return []
        except json.JSONDecodeError:
            print(f"❌ JSON decode error in: {self.path}")
            return []

    def get_all(self) -> List[Dict]:
        return self.requirements

    def get_by_user_group(self, user_group: str) -> List[Dict]:
        return [r for r in self.requirements if r["userGroup"] == user_group]

    def get_by_pillar(self, pillar: str) -> List[Dict]:
        return [r for r in self.requirements if r["pillar"] == pillar]

    def get_by_user_group_and_pillar(self, user_group: str, pillar: str) -> List[Dict]:
        return [r for r in self.requirements if r["userGroup"] == user_group and r["pillar"] == pillar]
