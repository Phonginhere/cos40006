import json
import os
from utils import load_alfred_summary, load_user_group_summary, get_llm_response, CURRENT_LLM
from raw_requirement_loader import RawRequirementLoader
from typing import List, Dict

# Output path
OUTPUT_DIR = os.path.join("results", CURRENT_LLM)
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "raw_requirements.json")

# PILLAR NAMES
PILLARS = [
    "Pillar 1 - User-Driven Interaction Assistant",
    "Pillar 2 - Personalized Social Inclusion",
    "Pillar 3 - Effective & Personalized Care",
    "Pillar 4 - Physical & Cognitive Impairments Prevention",
    "General Requirements"
]

USER_GROUP_MAP = {
    "Older Adults": "older_adults",
    "Caregivers and Medical Staff": "caregivers_and_medical_staff",
    "Developers and App Creators": "developers_and_app_creators"
}

USER_GROUPS = list(USER_GROUP_MAP.keys())

# Build LLM prompt
def build_pillar_prompt(user_group: str, pillar_name: str, previous_reqs: List[Dict]) -> str:
    alfred_summary = load_alfred_summary()
    internal_key = USER_GROUP_MAP[user_group]
    user_summary = load_user_group_summary(internal_key)

    prior_text = ""
    if previous_reqs:
        prior_text = "\n\nTo avoid overlap across pillars, here are the requirement titles already defined in earlier stages. Please ensure your new requirements for this pillar are **distinct** from these:\n" + json.dumps(previous_reqs, indent=2)

    return f"""
You are a system analyst helping define **abstract, general-level functional/non-functional requirements** for a virtual assistant platform called ALFRED, fon one type of user group as below.

--- ALFRED SYSTEM SUMMARY ---
{alfred_summary}

--- USER GROUP CONTEXT: {user_group} ---
{user_summary}

Your task is to generate a JSON array of **7 to 10 broad and abstract capability areas** for the ALFRED system, specifically for the above user group and the below pillar:

🧱 Pillar Focus: {pillar_name}

⚠️ IMPORTANT: Avoid repeating items from previous pillars. {prior_text}

FORMAT: Each item should be **brief, abstract, and general**. Avoid specifics like feature implementation, target age, or UI details. We only want minimal raw requirements that will later be turned into fully developed user stories. Please generate **7 to 10** requirements in a JSON array. Each requirement should have:
- "title": A concise title summarizing the requirement
- "subOptions": A list of 3 to 6 more specific or optional refinements/variations

📤 Output format:
[
  {{
    "title": "...",
    "subOptions": []
  }},
  ...
]

Example below (DO NOT rely 100% on this example. This is just to help you understand the format and level of detail expected in the output. The real requirements (title, subObtions, subObtions's count, etc.) should be based on the user group summary (as specified above) and ALFRED system summary you’ve been provided, and they should reflect the specific needs of the given User group in relation to the ALFRED system.):
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

Note: 
- Please try to diversify your 7-10 requirements set across different areas based on the ALFRED system, the pillar focus and the given user group.
- Strictly, do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""

# Enrich output with ID, pillar, userGroup
def enrich_general_requirements(raw: List[Dict], user_group: str, pillar: str, index: int) -> List[Dict]:
    enriched = []
    for i, item in enumerate(raw):
        enriched.append({
            "id": f"RREQ-{index + i:03}",
            "pillar": pillar,
            "userGroup": user_group,
            "title": item["title"],
            "subOptions": item.get("subOptions", [])
        })
    return enriched

# Generate raw requirements for one user group
def generate_generalized_for_group(user_group: str, start_index: int) -> (List[Dict], int):
    results = []
    prior_titles = []

    for pillar in PILLARS:
        print(f"🧠 Generating for {user_group} — {pillar}")
        prompt = build_pillar_prompt(user_group, pillar, prior_titles)
        response = get_llm_response(prompt)

        try:
            data = json.loads(response)
            enriched = enrich_general_requirements(data, user_group, pillar, start_index)
            results.extend(enriched)
            prior_titles.extend([r["title"] for r in data])
            start_index += len(data)
        except Exception as e:
            print(f"❌ Failed to parse JSON for {user_group} / {pillar}: {e}")
            continue

    return results, start_index

# Main generator
def generate_all_raw_requirements():
    loader = RawRequirementLoader(OUTPUT_FILE)
    if loader.get_all():
        print(f"📂 Generalized raw requirements already exist. Skipping.")
        return

    all_reqs = []
    global_index = 1

    for group in USER_GROUPS:
        print(f"\n🚀 Generating for user group: {group}")
        group_reqs, global_index = generate_generalized_for_group(group, global_index)
        all_reqs.extend(group_reqs)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_reqs, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved {len(all_reqs)} generalized requirements to {OUTPUT_FILE}")