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
- "title": A concise title summarizing the capability blueprint. It should be general, minimal, and system-level
- "subOptions": A list of 3 to 6 more specific or optional refinements/variations. The aim of each subOption is a method to deliver the capability blueprint effectively and efficiently, which is specified in "title". The subOptions are diverse, non-overlapping, and sometimes even mutually EXCLUSIVE, and the number of subOptions should be flexible (and considered carefully) between 3 and 6 to ensure all possible options of capability blueprints are listed.
Alternatively,  varying the number of subOptions between 3 and 6 is a very smart way to reflect:
  + The conceptual depth of each capability,
  + The realistic delivery diversity,
  + And your’s ability to infer minimal or expanded options.

📤 Output format:
[
  {{
    "title": "...",
    "subOptions": []
  }},
  ...
]

Example below (DO NOT rely 100% on this example. This is just to help you understand the format and level of detail expected in the output. The real capability blueprints (title, subObtions, subObtions's count, etc.) should be based on the user group summary (as specified above) and ALFRED system summary you’ve been provided, and they should reflect the specific needs of the given User group in relation to the ALFRED system.):

Example 1: Based on user group "Older Adults", and Pillar 1 - User-Driven Interaction Assistant
[
  {{
    "title": "Personalized Daily Routines",
    "subOptions": [
      "Voice-based wake-up reminders",
      "Automated agenda recaps in the morning",
      "Routine summary and suggestions in the evening"
    ]
  }},
  {{
    "title": "Environment-Aware Assistance",
    "subOptions": [
      "Adjust responses based on current location",
      "Voice interaction changes based on time of day",
      "Proactive prompts when users appear inactive",
      "Seasonal adaptation of guidance and reminders",
      "Alert suppression during quiet hours"
    ]
  }},
  ...
]

Example 2: Based on user group "Older Adults", and Pillar 2 - Personalized Social Inclusion
[
  {{
    "title": "Enhanced Social Connectivity",
    "subOptions": [
      "Voice-managed contact directory",
      "Scheduled calls with friends or family",
      "Automated invitations to local events"
    ]
  }},
  {{
    "title": "Memory-Aware Reminders",
    "subOptions": [
      "Birthday and anniversary prompts",
      "Voice-recorded personal notes replay",
      "Suggestions to reconnect with missed contacts",
      "Family update digest delivery"
    ]
  }},
  ...
]

Example 3: Based on user group "Caregivers and Medical Staff", and Pillar 1 - User-Driven Interaction Assistant
[
  {{
    "title": "Remote Emergency Intervention Support",
    "subOptions": [
      "Instant voice-based SOS relay",
      "Automated fallback contact escalation",
      "Caregiver override for command injection",
      "Context-aware emergency scenario detection"
    ]
  }},
  {{
    "title": "Medication Query Interface",
    "subOptions": [
      "Voice-driven pill identification",
      "Medication side effect lookup",
      "Usage clarification through scenario prompts",
      "Time-based dosage confirmation via voice"
    ]
  }},
  ...
]

Example 4: Based on user group "Caregivers and Medical Staff", and Pillar 3 - Effective & Personalized Care
[
  {{
    "title": "Vital Data Monitoring Framework",
    "subOptions": [
      "Real-time pulse and heart rate visualization",
      "Trend detection over rolling 7-day intervals",
      "Configurable caregiver alert thresholds"
    ]
  }},
  {{
    "title": "User Localization Support",
    "subOptions": [
      "BLE/GPS switching based on indoor/outdoor context",
      "Geo-fencing alerts for risk zones",
      "Map-based caregiver dashboard integration",
      "Historical movement heatmaps",
      "Proximity alerts to prevent wandering",
      "Speech-triggered location inquiry"
    ]
  }},
  ...
]

Example 5: Based on user group "Caregivers and Medical Staff", and General Requirements
[
  {{
    "title": "Secure Communication Channels",
    "subOptions": [
      "Encrypted voice and video calls",
      "Timed message access",
      "Message self-destruct timers",
      "Access logs for message viewing"
    ]
  }},
  {{
    "title": "Cross-Device Access Portability",
    "subOptions": [
      "Profile syncing across caregiver devices",
      "Temporary role delegation for shift coverage",
      "Low-bandwidth fallback interaction mode",
      "Device-specific feature enablement toggles"
    ]
  }},
  ...
]

Example 6: Based on user group "Developers and App Creators", and Pillar 1 - User-Driven Interaction Assistant
[
  {{
    "title": "Voice Interaction Toolkit for Developers",
    "subOptions": [
      "Open API for adding new commands",
      "Replay debugger for intent misfires",
      "Real-time sandbox simulation",
      "Feedback analytics for command usage",
      "Test suite generation for voice flows"
    ]
  }},
  {{
    "title": "Feature Flag Support in Deployment",
    "subOptions": [
      "Rollout scheduling across user cohorts",
      "Control group selection for voice interaction experiments",
      "Dynamic disabling of unstable commands",
      "Audit logging per feature toggle action"
    ]
  }},
  ...
]

Example 7: Based on user group "Developers and App Creators", and General Requirements
[
  {{   
    "title": "Compliance-Aware Development Tools",
    "subOptions": [
      "Templates for privacy policy generation",
      "Version-controlled legal disclaimer blocks",
      "CI/CD plugins for consent validation",
      "Interactive checklists aligned with ISO/HIPAA standards"
    ]
  }},
  {{
    "title": "System Status and Debugging Framework",
    "subOptions": [
      "Crash event timeline reconstruction",
      "Real-time server health widget",
      "Log streaming API for external dashboards"
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