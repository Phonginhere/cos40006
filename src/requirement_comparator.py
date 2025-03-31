import os
import json
from collections import defaultdict
from typing import List, Dict
from requirement_generator import Requirement, RequirementLoader
from llm_handler import get_gpt_4o_mini_response
from utils import load_requirement_tags

class RequirementComparator:
    def __init__(self, requirements: Dict[str, List[Requirement]], output_dir=r"results\merged_requirements"):
        self.requirements = requirements  # Dict[persona_name] -> List[Requirement]
        self.output_dir = output_dir
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
        """
        Builds a comparison prompt for requirements under a tag.
        """
        examples = "\n\n".join([
            f"Requirement {i+1}:\n"
            f"- ID: {r.id}\n"
            f"- Name: {r.name}\n"
            f"- Description: {r.description}\n"
            f"- Type: {r.type}\n"
            f"- Personas: {', '.join(r.use_cases)}"
            for i, r in enumerate(requirements)
        ])

        prompt = f"""You are performing comparative analysis of software requirements from different user personas.

All the following requirements are categorized under the tag: "{tag}".

Compare them and return the following:
1. Group requirements that are **functionally similar** (can be merged or unified).
2. Detect any **conflicting goals or assumptions**.
3. Suggest **a unified version** of each matching group if possible.

Format:
{{
  "Tag": "Health_Support",
  "MatchingGroups": [
    {{
      "GroupID": "G1",
      "OriginalRequirements": [<IDs>],
      "MergedSuggestion": {{
        "ID": "FR-M01",
        "Name": "...",
        "Description": "...",
        "SourcePersonas": [list of persona names]
      }}
    }}
  ],
  "Conflicts": [
    {{
      "Req1": "<ID>",
      "Req2": "<ID>",
      "ConflictType": "...",
      "Note": "..."
    }}
  ]
}}

Strictly return valid JSON only. No bullet points or markdown. Avoid special formatting like bold/italic.
Here are the requirements:

{examples}
"""
        return prompt

    def analyze_tag(self, tag: str, requirements: List[Requirement]) -> Dict:
        """Analyzes one tag group using the LLM and returns parsed JSON."""
        prompt = self.build_prompt_for_tag(tag, requirements)
        response = get_gpt_4o_mini_response(prompt)
        
        # 👇 Output full raw LLM response for inspection
        print(f"\n📤 Raw LLM response for tag '{tag}':\n{'-'*60}")
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
        """
        Perform comparative analysis:
        - If no tags are provided, analyze all tags.
        - If a list of tag strings is provided, analyze only those tags.
        """
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

