import json
import os
from utils import load_alfred_summary, load_user_group_summary, get_llm_response, CURRENT_LLM, PILLARS, USER_GROUP_KEYS, USER_GROUPS, CAPABILITY_BLUEPRINTS_FILE
from capability_blueprint_loader import CapabilityBlueprintLoader
from typing import List, Dict


# Build LLM prompt
def build_pillar_prompt(user_group: str, pillar_name: str, previous_cbs: List[Dict]) -> str:
    alfred_summary = load_alfred_summary()
    internal_key = USER_GROUP_KEYS[user_group]
    user_summary = load_user_group_summary(internal_key)

    prior_text = ""
    if previous_cbs:
        prior_text = "\n\nTo avoid overlap across pillars, here are the capability blueprint titles already defined in earlier stages. Please ensure your new capability blueprints for this pillar are **distinct** from these:\n" + json.dumps(previous_cbs, indent=2)

    return f"""
You are a system analyst helping define **abstract, general-level functional/non-functional capability blueprints** for a virtual assistant platform called ALFRED, fon one type of user group as below.

--- ALFRED SYSTEM SUMMARY ---
{alfred_summary}

--- USER GROUP CONTEXT: {user_group} ---
{user_summary}

Your task is to generate a JSON array of **7 to 10 broad and abstract capability areas** for the ALFRED system, specifically for the above user group and the below pillar:

🧱 Pillar Focus: {pillar_name}

⚠️ IMPORTANT: Avoid repeating items from previous pillars. {prior_text}

FORMAT: Each item should be **brief, abstract, and general**. Avoid specifics like feature implementation, target age, or UI details. We only want minimal capability blueprints that will later be turned into fully developed user stories. Please generate **7 to 10** capability blueprints in a JSON array. Each capability blueprint should have:
- "title": A concise title summarizing the capability blueprint
- "subOptions": A list of 3 to 6 more specific or optional refinements/variations. The aim of each subOption is a method to deliver the capability blueprint effectively and efficiently, which is specified in "title". Each subOption should be unique enough from each other, and the number of subOptions should be flexible (and considered carefully) between 3 and 6 to ensure all possible options of capability blueprints are listed.

📤 Output format:
[
  {{
    "title": "...",
    "subOptions": []
  }},
  ...
]

Example below (DO NOT rely 100% on this example. This is just to help you understand the format and level of detail expected in the output. The real capability blueprints (title, subObtions, subObtions's count, etc.) should be based on the user group summary (as specified above) and ALFRED system summary you’ve been provided, and they should reflect the specific needs of the given User group in relation to the ALFRED system.):
- Example 1: Based on User group "Caregivers and Medical Staff" and Pillar 3 - Effective & Personalized Care
[
  {{
    "title": "Accessible Client Health Data Interfaces",
    "subOptions": [
      "Voice-based interaction for data retrieval",
      "Tactile interface with summaries and alerts",
      "Real-time dashboards with customizable views",
      "Offline access to basic health stats"
    ]
  }},
  ...
]

Example 2: Based on User group "Older Adults", and pillar "General Requirements"
[
  {{
    "title": "Privacy-Preserving Voice Command Recognition",
    "subOptions": [
      "On-device voice processing to avoid cloud dependencies",
      "Selective data sharing with configurable permissions",
      "User confirmation before sensitive actions are taken",
      "Local storage for personal logs with encryption",
      "Option to disable listening during private hours"
    ]
  }},
  ...
]

Also, note that these examples are not based on the same user group and pillar, therefore they are not a the same set of 7-10 capability blueprints.

⚠️ NOTE: 
- Please try to diversify your 7-10 capability blueprints set across different areas based on the ALFRED system, the pillar focus and the given user group.
- Strictly, do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""

# Enrich output with ID, pillar, userGroup
def enrich_general_capability_blueprints(raw: List[Dict], user_group: str, pillar: str, index: int) -> List[Dict]:
    enriched = []
    for i, item in enumerate(raw):
        enriched.append({
            "id": f"CB-{index + i:03}",
            "pillar": pillar,
            "userGroup": user_group,
            "title": item["title"],
            "subOptions": item.get("subOptions", [])
        })
    return enriched

# Generate capability blueprints for one user group
def generate_generalized_for_group(user_group: str, start_index: int) -> (List[Dict], int):
    results = []
    prior_titles = []

    for pillar in PILLARS:
        print(f"🧠 Generating for {user_group} — {pillar}")
        prompt = build_pillar_prompt(user_group, pillar, prior_titles)
        response = get_llm_response(prompt)

        try:
            data = json.loads(response)
            enriched = enrich_general_capability_blueprints(data, user_group, pillar, start_index)
            results.extend(enriched)
            prior_titles.extend([r["title"] for r in data])
            start_index += len(data)
        except Exception as e:
            print(f"❌ Failed to parse JSON for {user_group} / {pillar}: {e}")
            continue

    return results, start_index

# Main generator
def generate_all_capability_blueprints():
    loader = CapabilityBlueprintLoader(CAPABILITY_BLUEPRINTS_FILE)
    if loader.get_all():
        print(f"📂 Generalized capability blueprints already exist. Skipping.")
        return

    all_cbs = []
    global_index = 1

    for group in USER_GROUPS:
        print(f"\n🚀 Generating for user group: {group}")
        group_cbs, global_index = generate_generalized_for_group(group, global_index)
        all_cbs.extend(group_cbs)

    with open(CAPABILITY_BLUEPRINTS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_cbs, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved {len(all_cbs)} generalized capability blueprints to {CAPABILITY_BLUEPRINTS_FILE}")