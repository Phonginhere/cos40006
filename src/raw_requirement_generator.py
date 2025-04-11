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

# Build LLM prompt
def build_pillar_prompt(user_group: str, pillar_name: str, previous_reqs: List[Dict]) -> str:
    alfred_summary = load_alfred_summary()
    user_summary = load_user_group_summary(user_group)

    prior_text = ""
    if previous_reqs:
        prior_text = "\n\nTo avoid overlap across pillars, here are the requirement titles already defined in earlier stages. Please ensure your new requirements for this pillar are **distinct** from these:\n" + json.dumps(previous_reqs, indent=2)

    return f"""
You are a system analyst helping define core functional requirements for a virtual assistant platform called ALFRED.

--- ALFRED SYSTEM SUMMARY ---
{alfred_summary}

--- USER GROUP CONTEXT: {user_group.replace("_", " ").title()} ---
{user_summary}

Your task is to write a list of **6 to 10** abstract, high-level capability titles of functional/non-funcational requirements for the ALFRED platform, specifically for the above user group, and:

🧱 Pillar Focus: {pillar_name}

{prior_text}

Each item should be **brief and general**. Avoid specifics like feature implementation, target age, or UI details. We only want minimal raw requirements that will later be turned into fully developed user stories. Please generate **6 to 10** requirements in a JSON array. Each requirement should have:
- "title": A concise title summarizing the requirement
- "priority": from 1 to 5 (Use the number only. For example: `"priority": "2"` — do not use words like "High", "Low", or "Medium". Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.), where:
  1 = Very high priority. Will be implemented.
  2 = High priority. Important for the ALFRED system; an implementation is planned.
  3 = Normal priority. Will be implemented if resources are available.
  4 = Low priority. Only considered if synergies with other stories exist.
  5 = Out of scope. Will not be implemented.
  
Note: Please try to diversify your requirements set across different areas based on the ALFRED system, and different priority levels (1 to 5).

📤 Output format:
[
  {{
    "title": "...",
    "priority": "1"
  }},
  ...
]

Example below (DO NOT rely 100% on this example. This is just to help you understand the format and level of detail expected in the output. The requirements should be based on the user group summary (as specified above) and ALFRED system summary you’ve been provided, and they should reflect the specific needs of the given User group in relation to the ALFRED system.):
[
  {{
    "title": "Voice-Activated Commands",
    "priority": "2"
  }}
]

Strictly, do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""

# Enrich with id, pillar, user group
def enrich_requirements(requirements: List[Dict], user_group: str, pillar: str, start_index: int) -> List[Dict]:
    enriched = []
    for i, req in enumerate(requirements):
        enriched.append({
            "id": f"RREQ-{start_index + i:03}",
            "pillar": pillar,
            "userGroup": user_group.replace("_", " ").title().replace("And", "and"),
            **req
        })
    return enriched

# Generate raw requirements for one user group
def generate_raw_requirements_for_user_group(user_group: str, start_index: int) -> (List[Dict], int):
    all_reqs = []
    prev_reqs = []

    for pillar in PILLARS:
        prompt = build_pillar_prompt(user_group, pillar, prev_reqs)
        print(f"🧠 Generating for {user_group} — {pillar}...")
        response = get_llm_response(prompt)

        try:
            raw = json.loads(response)
            enriched = enrich_requirements(raw, user_group, pillar, start_index)
            all_reqs.extend(enriched)
            prev_reqs.extend(raw)
            start_index += len(raw)
        except Exception as e:
            print(f"❌ Error parsing JSON for {user_group} / {pillar}: {e}")
            continue

    return all_reqs, start_index

# Main generator
def generate_all_raw_requirements():
    loader = RawRequirementLoader(OUTPUT_FILE)
    if loader.get_all():
        print(f"📂 Raw requirements already exist at {OUTPUT_FILE}. Skipping generation.")
        return

    user_groups = ["older_adults", "caregivers_and_medical_staff", "developers_and_app_creators"]
    all_requirements = []
    global_index = 1

    for group in user_groups:
        print(f"\n🚀 Generating raw requirements for: {group}")
        group_reqs, global_index = generate_raw_requirements_for_user_group(group, global_index)
        all_requirements.extend(group_reqs)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_requirements, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Done! All raw requirements saved to {OUTPUT_FILE}")