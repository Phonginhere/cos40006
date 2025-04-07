import os
import json
from collections import defaultdict
from typing import List
from user_persona_loader import UserPersona
from llm_handler import get_llm_response, CURRENT_LLM
from utils import load_alfred_summary, load_use_case_tags

# Load external content
ALFRED_SUMMARY = load_alfred_summary()
USE_CASE_TAGS = load_use_case_tags()

class UseCaseGenerator:
    def __init__(self, personas: List[UserPersona]):
        self.personas = personas
        self.tag_map = defaultdict(list)

    def generate_tags_with_llm(self):
        print("🔎 Generating persona tags using LLM...")
        for persona in self.personas:
            persona_summary = f"""
ID: {persona.id}
Name: {persona.name}
Tagline: {persona.tagline}
Core Goals: {', '.join(persona.core_goals)}
Typical Challenges: {', '.join(persona.typical_challenges)}
Main Tasks: {', '.join(persona.main_tasks)}
"""

            tag_list = ", ".join(USE_CASE_TAGS)
            prompt = f"""You are analyzing a user persona for a digital assistant designed for older adults (ALFRED).

Given the following persona details:

{persona_summary}

Return a list of short, relevant system-level tags that describe this persona’s needs or attributes. 
Choose from this tag list: [{tag_list}]

Return ONLY the tags in valid Python list format (e.g. ["Social_Connection", "Voice_Pref"]).
"""

            response = get_llm_response(prompt)

            try:
                tags = eval(response) if response.startswith("[") else []
            except Exception:
                print(f"⚠️ Could not parse tags for {persona.name}: {response}")
                tags = []

            for tag in tags:
                self.tag_map[tag].append(persona)

        tag_summary = {
            persona.name: [tag for tag, ppl in self.tag_map.items() if persona in ppl]
            for persona in self.personas
        }

        result_dir = os.path.join("results", CURRENT_LLM)
        os.makedirs(result_dir, exist_ok=True)

        with open(os.path.join(result_dir, "generated_tags.json"), "w", encoding="utf-8") as f:
            json.dump(tag_summary, f, indent=4)
        print(f"✅ Tag summary saved to: {os.path.join(result_dir, 'generated_tags.json')}")

    def generate_use_case_prompt(self, tag: str, personas: List[UserPersona]) -> str:
        summary = "\n".join([
            f"- {p.name}: {p.tagline}" for p in personas[:3]  # limit to 3
        ])

        return f"""{ALFRED_SUMMARY}

Generate one realistic use case shared by older adults under the tag "{tag}".
Here are some relevant personas:
{summary}

Strictly, please do NOT use any markdown, bold, italic, or special formatting in your response.

Use case format:
Use case ID: UC-XXX
Use case name: [Short and action-oriented]
Personas: [IDs of the personas involved]
Use case description: [Concise narrative of the use case in 4–6 sentences]
"""

    def generate_use_cases(self, output_dir=None) -> List['UseCase']:
        if output_dir is None:
            output_dir = os.path.join("results", CURRENT_LLM, "use_cases")
        self.generate_tags_with_llm()
        os.makedirs(output_dir, exist_ok=True)

        uc_counter = 1
        use_cases = []

        for tag, personas in self.tag_map.items():
            if len(personas) < 2:
                continue

            prompt = self.generate_use_case_prompt(tag, personas)
            response = get_llm_response(prompt)

            if response:
                uc_id = f"UC-{uc_counter:03d}"
                file_data = {
                    "ID": uc_id,
                    "Name": self.extract_title(response),
                    "Personas": [p.id for p in personas],
                    "Description": self.extract_description(response)
                }

                filename = os.path.join(output_dir, f"{uc_id}.json")
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(file_data, f, indent=4, ensure_ascii=False)

                print(f"📄 Saved {uc_id} to {filename}")
                uc_counter += 1
                use_cases.append(UseCase(file_data))

        return use_cases

    def extract_title(self, response: str) -> str:
        for line in response.splitlines():
            if line.lower().startswith("use case name:"):
                return line.split(":", 1)[1].strip()
        return "Untitled"

    def extract_description(self, response: str) -> str:
        capturing = False
        description_lines = []

        for line in response.splitlines():
            if line.lower().startswith("use case description:"):
                inline = line.split(":", 1)[1].strip()
                if inline:
                    return inline
                capturing = True
                continue
            if capturing and line.strip():
                description_lines.append(line.strip())
            elif capturing and not line.strip():
                break

        return " ".join(description_lines).strip()


# ==========================================================================

class UseCase:
    def __init__(self, data: dict):
        self.id = data.get("ID", "UC-XXX")
        self.name = data.get("Name", "Untitled Use Case")
        self.personas = data.get("Personas", [])
        self.description = data.get("Description", "")

    def __repr__(self):
        return f"UseCase(ID={self.id}, Name={self.name})"

    def display(self):
        print(f"\n📌 Use Case: {self.id}")
        print(f"   - Name: {self.name}")
        print(f"   - Personas: {', '.join(self.personas)}")
        print(f"   - Description: {self.description}")


class UseCaseLoader:
    def __init__(self, use_case_dir=None):
        if use_case_dir is None:
            use_case_dir = os.path.join("results", CURRENT_LLM, "use_cases")
        self.use_case_dir = use_case_dir
        self.use_cases: List[UseCase] = []

    def load(self) -> List[UseCase]:
        if not os.path.exists(self.use_case_dir):
            print(f"❌ Use case directory '{self.use_case_dir}' does not exist.")
            return []

        for filename in os.listdir(self.use_case_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.use_case_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.use_cases.append(UseCase(data))
                except Exception as e:
                    print(f"⚠️ Failed to load {filename}: {e}")

        print(f"✅ Loaded {len(self.use_cases)} use case(s) from '{self.use_case_dir}'")
        return self.use_cases

    def get_use_cases(self) -> List[UseCase]:
        return self.use_cases

    def print_all_use_cases(self):
        if not self.use_cases:
            print("❌ No use cases loaded.")
            return
        for uc in self.use_cases:
            uc.display()
