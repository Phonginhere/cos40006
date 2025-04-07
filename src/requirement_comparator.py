import os
import json
from collections import defaultdict
from typing import List, Dict
from requirement_generator import Requirement, RequirementLoader
from llm_handler import get_llm_response, CURRENT_LLM
from utils import load_requirement_tags


class RequirementComparator:
    def __init__(self, requirements: Dict[str, List[Requirement]], output_dir=None):
        self.requirements = requirements  # Dict[persona_name] -> List[Requirement]
        self.output_dir = output_dir or os.path.join("results", CURRENT_LLM, "merged_requirements")
        self.tag_map = defaultdict(list)  # tag -> list of Requirement instances
        self.tags = load_requirement_tags()

    def group_by_tag(self):
        """Builds tag-based index of all requirements."""
        for persona, reqs in self.requirements.items():
            for req in reqs:
                for tag in req.tags:
                    self.tag_map[tag].append(req)
        print(f"📌 Grouped requirements into {len(self.tag_map)} tag categories.")

    def build_prompt_for_tag(self, tag: str, requirements: List[Requirement]) -> str:
        examples = "\n\n".join([
            f"Requirement {i+1}:\n"
            f"- ID: {r.id}\n"
            f"- Name: {r.name}\n"
            f"- Description: {r.description}\n"
            f"- Type: {r.type}\n"
            f"- Personas: {', '.join(r.use_cases)}"
            for i, r in enumerate(requirements)
        ])

        prompt = f"""
You are performing a **comparative analysis of system requirements** created for different user personas.

All the following requirements are categorized under the tag: "{tag}".

Your task:
1. **Group similar requirements** and describe the key similarities and differences.
2. **Identify all conflicts or inconsistencies**, including even small mismatches in:
    - Functionality overlap or divergence
    - Interaction modality differences (voice, touch, wearable, etc.)
    - Assumptions about user capability (e.g. physical, cognitive, digital literacy)
    - Device or environmental context constraints
    - Frequency and scheduling of actions
    - Data privacy, access, and user control
    - Personalization vs. consistency conflicts
    - Security level or compliance differences (e.g. GDPR, HIPAA)
    - UX trade-offs: simplicity vs. control, automation vs. transparency
3. **Explain the root cause of each conflict** based on the personas’ perspectives.
4. Suggest a **unified requirement** when feasible that harmonizes differences.
5. Ensure traceability of merged/conflicting requirements by ID.

Your output must follow this structure (strict JSON only, no markdown):

{{
  "Tag": "{tag}",
  "SimilarGroups": [
    {{
      "GroupID": "G1",
      "OriginalRequirements": [<IDs>],
      "SimilarityNote": "...explain what is shared or equivalent...",
      "DifferenceNote": "...explain how they differ...",
      "UnifiedRequirement": {{
        "ID": "FR-M01",
        "Name": "...",
        "Description": "...",
        "SourcePersonas": [<persona IDs>]
      }}
    }}
  ],
  "Conflicts": [
    {{
      "Req1": "<ID>",
      "Req2": "<ID>",
      "ConflictType": "...e.g., Security vs. Simplicity...",
      "PersonaConflict": "...e.g., Developer vs Compliance Officer...",
      "Note": "...explanation of the conflict..."
    }}
  ]
}}

Strictly return valid JSON only. No bullet points or markdown. Avoid special formatting like bold/italic.
Here are the requirements:

{examples}
"""

        return prompt

    def analyze_tag(self, tag: str, requirements: List[Requirement]) -> Dict:
        prompt = self.build_prompt_for_tag(tag, requirements)
        response = get_llm_response(prompt)

        print(f"\n📤 Raw LLM response for tag '{tag}':\n{'-' * 60}")
        print(response)
        print('-' * 60)

        if not response:
            print(f"⚠️ No LLM response for tag '{tag}'")
            return {}

        try:
            result = json.loads(response)
            return result
        except Exception as e:
            print(f"❌ Failed to parse response for tag '{tag}': {e}")
            return {}

    def run(self, tags_to_compare: List[str] = None):
        self.group_by_tag()
        os.makedirs(self.output_dir, exist_ok=True)

        tags_to_process = tags_to_compare if tags_to_compare else list(self.tag_map.keys())

        for tag in tags_to_process:
            requirements = self.tag_map.get(tag, [])
            if len(requirements) < 2:
                print(f"⚠️ Skipping tag '{tag}' (not enough requirements).")
                continue

            print(f"\n🔍 Analyzing tag: {tag} ({len(requirements)} requirements)")
            result = self.analyze_tag(tag, requirements)

            if result:
                filename = os.path.join(self.output_dir, f"{tag.lower()}.json")
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=4, ensure_ascii=False)
                print(f"✅ Saved analysis to: {filename}")
