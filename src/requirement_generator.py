import os
import json
from typing import List, Dict
from user_persona_loader import UserPersona
from use_case_generator import UseCase
from llm_handler import get_gpt_4o_mini_response
from utils import load_requirement_tags, load_alfred_summary

# Load ALFRED content
ALFRED_SUMMARY = load_alfred_summary()
ALFRED_TAGS = load_requirement_tags()

class RequirementGenerator:
    def __init__(self, personas: List[UserPersona], use_cases: List[UseCase]):
        self.personas = personas
        self.use_cases = use_cases

    def find_use_cases_for_persona(self, persona_id: str) -> List[UseCase]:
        return [uc for uc in self.use_cases if persona_id in uc.personas]

    def generate_prompt(self, persona: UserPersona, associated_use_cases: List[UseCase]) -> str:
        use_case_descriptions = "\n".join([
            f"{uc.id}: {uc.name} — {uc.description}" for uc in associated_use_cases
        ]) or "None"

        persona_summary = f"""
ID: {persona.id}
Name: {persona.name}
Tagline: {persona.tagline}
Demographics: {json.dumps(persona.demographic_data, indent=2)}
Core Goals: {', '.join(persona.core_goals)}
Challenges: {', '.join(persona.typical_challenges)}
Tasks: {', '.join(persona.main_tasks)}
Most Important Tasks: {', '.join(persona.most_important_tasks)}
Expertise: {persona.expertise}
Misc: {', '.join(persona.miscellaneous) if isinstance(persona.miscellaneous, list) else persona.miscellaneous}
"""

        tags_str = ", ".join(ALFRED_TAGS)

        prompt = f"""{ALFRED_SUMMARY}

Based on the following user persona and the use cases they are involved in, generate a list of system requirements.

--- USER PERSONA ---
{persona_summary}

--- USE CASES ---
{use_case_descriptions}

Generate:
- 3–6 functional requirements
- 2–3 non-functional requirements

Each requirement must include:
- ID (start with "{persona.id}-FR-" or "{persona.id}-NFR-")
- Name
- Description
- Related use case IDs (from above)
- Tags: Choose 1–3 from the following list to categorize each requirement:
[{tags_str}]

Respond in valid JSON format like this:
{{
  "FunctionalRequirements": [
    {{
      "ID": "{persona.id}-FR-001",
      "Name": "Short descriptive title",
      "Description": "Full description of the functional requirement...",
      "UseCases": ["UC-001"],
      "Tags": ["Event_Management", "User_Interaction"]
    }},
    ...
  ],
  "NonFunctionalRequirements": [
    {{
      "ID": "{persona.id}-NFR-001",
      "Name": "Short descriptive title",
      "Description": "Full description of the non-functional requirement...",
      "UseCases": ["UC-002"],
      "Tags": ["Accessibility", "Usability"]
    }},
    ...
  ]
}}

Strictly, please do NOT use any markdown, bold, italic, or special formatting in your response.
"""
        return prompt

    def generate_requirements(self, output_dir=r"results/requirements"):
        os.makedirs(output_dir, exist_ok=True)

        for persona in self.personas:
            print(f"🧠 Generating requirements for persona: {persona.name}")
            associated_use_cases = self.find_use_cases_for_persona(persona.id)
            prompt = self.generate_prompt(persona, associated_use_cases)
            response = get_gpt_4o_mini_response(prompt)

            if response:
                try:
                    req_data = json.loads(response)
                    file_name = persona.name.lower().replace(" ", "_") + "_requirements.json"
                    output_path = os.path.join(output_dir, file_name)

                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(req_data, f, indent=4, ensure_ascii=False)

                    print(f"✅ Saved requirements for {persona.name} to {output_path}")
                except Exception as e:
                    print(f"❌ Failed to parse or save requirements for {persona.name}: {e}")
            else:
                print(f"⚠️ No response for {persona.name}")


# ==========================================================================

class Requirement:
    def __init__(self, data: Dict, rtype: str):
        self.id = data.get("ID")
        self.name = data.get("Name")
        self.description = data.get("Description")
        self.use_cases = data.get("UseCases", [])
        self.tags = data.get("Tags", [])
        self.type = rtype  # "Functional" or "NonFunctional"

    def __repr__(self):
        return f"{self.id}: {self.name} ({self.type})"


class RequirementLoader:
    def __init__(self, folder=r"results\requirements"):
        self.folder = folder
        self.requirements: Dict[str, List[Requirement]] = {}  # persona name → list of Requirement

    def load(self) -> Dict[str, List[Requirement]]:
        if not os.path.exists(self.folder):
            print(f"❌ Requirement folder '{self.folder}' not found.")
            return {}

        for filename in os.listdir(self.folder):
            if filename.endswith("_requirements.json"):
                persona_name = filename.replace("_requirements.json", "").replace("_", " ").title()

                path = os.path.join(self.folder, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.requirements[persona_name] = []

                        for fr in data.get("FunctionalRequirements", []):
                            self.requirements[persona_name].append(Requirement(fr, "Functional"))

                        for nfr in data.get("NonFunctionalRequirements", []):
                            self.requirements[persona_name].append(Requirement(nfr, "NonFunctional"))
                except Exception as e:
                    print(f"⚠️ Failed to load {filename}: {e}")

        print(f"✅ Loaded requirements for {len(self.requirements)} persona(s)")
        return self.requirements
