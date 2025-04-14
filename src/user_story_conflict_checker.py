import os
import json
import pandas as pd
from typing import List, Dict
from utils import get_llm_response, load_alfred_summary, FINAL_USER_STORY_DIR


def load_user_stories(persona_id: str, user_group_folder: str, pillar_file: str) -> List[Dict]:
    path = os.path.join(FINAL_USER_STORY_DIR, user_group_folder, f"{persona_id}_user_stories", pillar_file)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def build_conflict_prompt(alfred_summary: str, stories_a: List[Dict], stories_b: List[Dict], persona_a: str, persona_b: str, pillar_name: str) -> str:
    return f"""
You are a system analyst reviewing the ALFRED system’s user stories for potential design conflicts.

--- ALFRED SYSTEM SUMMARY ---
{alfred_summary}

--- CONTEXT ---
The following two lists of user stories are from **different personas** (Persona A: {persona_a}, Persona B: {persona_b}) but for the **same pillar**: {pillar_name}.

Your task is to **detect genuine conflicts** between these user stories.
✅ Conflicts must involve **fundamentally incompatible goals, constraints, or requirements**.
❌ Do NOT flag trade-offs, minor differences, or synonyms as conflicts. Only identify situations where the system would struggle to support both requirements without negotiation or compromise.

--- USER STORIES FROM PERSONA A ({persona_a}) ---
{json.dumps(stories_a, indent=2)}

--- USER STORIES FROM PERSONA B ({persona_b}) ---
{json.dumps(stories_b, indent=2)}

--- OUTPUT FORMAT ---
Please return a JSON object with a list of conflicts:
{{
  "Conflicts": [
    {{
      "PersonaA": "{persona_a}",
      "PersonaB": "{persona_b}",
      "ConflictType": "Functional | Non-Functional | Ethical | Data Access | Privacy | UX | etc.",
      "Req1": "<user story ID from Persona A>",
      "Req2": "<user story ID from Persona B>",
      "Note": "Explain briefly why these two are incompatible."
    }},
    ...
  ]
}}

Only output this JSON object. Do not include any other commentary or markdown.
"""


def check_user_story_conflicts():
    alfred_summary = load_alfred_summary()
    output_dir = os.path.join("results", "conflict_analysis")
    os.makedirs(output_dir, exist_ok=True)

    persona_map: Dict[str, str] = {}  # persona_id -> user_group_folder
    all_stories: Dict[str, Dict[str, List[Dict]]] = {}  # persona_id -> {pillar_file: [stories]}

    # Load all stories from all groups and personas
    for user_group_folder in os.listdir(FINAL_USER_STORY_DIR):
        group_path = os.path.join(FINAL_USER_STORY_DIR, user_group_folder)
        if not os.path.isdir(group_path):
            continue
        for persona_dir in os.listdir(group_path):
            persona_id = persona_dir.replace("_user_stories", "")
            persona_map[persona_id] = user_group_folder
            all_stories.setdefault(persona_id, {})
            for pillar_file in os.listdir(os.path.join(group_path, persona_dir)):
                if pillar_file.endswith(".json"):
                    stories = load_user_stories(persona_id, user_group_folder, pillar_file)
                    if stories:
                        all_stories[persona_id][pillar_file] = stories

    # Compare each pair of personas on the same pillar file
    for pillar_file in ["pillar_1_user_stories.json", "pillar_2_user_stories.json",
                        "pillar_3_user_stories.json", "pillar_4_user_stories.json",
                        "general_user_stories.json"]:
        pillar_conflicts = []

        persona_ids = list(all_stories.keys())
        for i in range(len(persona_ids)):
            a_id = persona_ids[i]
            a_stories = all_stories[a_id].get(pillar_file)
            if not a_stories:
                continue
            for j in range(i + 1, len(persona_ids)):
                b_id = persona_ids[j]
                b_stories = all_stories[b_id].get(pillar_file)
                if not b_stories:
                    continue

                print(f"🔍 Checking {pillar_file} — {a_id} vs {b_id}")

                prompt = build_conflict_prompt(
                    alfred_summary, a_stories, b_stories,
                    a_id, b_id,
                    pillar_file.replace("_user_stories.json", "").replace("_", " ").title()
                )

                response = get_llm_response(prompt)
                try:
                    result = json.loads(response)
                    if result.get("Conflicts"):
                        a_map = {s["id"]: s for s in a_stories}
                        b_map = {s["id"]: s for s in b_stories}
                        for conflict in result["Conflicts"]:
                            req1 = conflict.get("Req1")
                            req2 = conflict.get("Req2")
                            conflict["Req1_Title"] = a_map.get(req1, {}).get("title", "")
                            conflict["Req1_Summary"] = a_map.get(req1, {}).get("summary", "")
                            conflict["Req2_Title"] = b_map.get(req2, {}).get("title", "")
                            conflict["Req2_Summary"] = b_map.get(req2, {}).get("summary", "")
                            pillar_conflicts.append(conflict)
                except Exception as e:
                    print(f"⚠️ Error parsing response for {a_id} vs {b_id}: {e}")

        if pillar_conflicts:
            output_path = os.path.join(output_dir, f"{pillar_file.replace('.json', '')}_conflicts.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({"Conflicts": pillar_conflicts}, f, indent=2, ensure_ascii=False)
            print(f"✅ Conflicts saved to: {output_path}")


def convert_conflict_jsons_to_csv(folder_path: str):
    """
    Convert all JSON files in a folder into CSVs with the same base filename.
    Each JSON file must have a "Conflicts" key containing a list of dictionaries.
    """
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            json_path = os.path.join(folder_path, filename)
            csv_path = os.path.join(folder_path, filename.replace(".json", ".csv"))

            with open(json_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            conflicts = data.get("Conflicts", [])
            if not conflicts:
                print(f"No conflicts found in {filename}, skipping.")
                continue

            df = pd.DataFrame(conflicts)
            df.to_csv(csv_path, index=False, encoding="utf-8")
            print(f"Saved {csv_path}")
