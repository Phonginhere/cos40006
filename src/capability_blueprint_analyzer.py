import os
import json
import pandas as pd
from utils import get_llm_response, load_alfred_summary, load_user_group_summary, CURRENT_LLM, PILLARS, USER_GROUP_KEYS, FILTERED_CAPABILITY_BLUEPRINTS_DIR, FILTERED_CAPABILITY_BLUEPRINT_SUMMARIES_DIR
from capability_blueprint_loader import CapabilityBlueprintLoader
from user_persona_loader import UserPersonaLoader



def build_relevance_prompt(persona, cb, alfred_summary, group_summary) -> str:
    return f"""
You are a system analyst helping to align system capabilities with user needs in the ALFRED project.

Below is an overview of the system and the user context.

--- ALFRED SYSTEM SUMMARY ---
{alfred_summary}

--- USER GROUP CONTEXT ---
{group_summary}

--- PERSONA OVERVIEW ---
{persona.to_prompt_string()}

--- CAPABILITY BLUEPRINT TITLE TO ANALYZE ---
Title: "{cb['title']}"
Pillar: "{cb['pillar']}"

Your task: Determine whether the above capability blueprint is relevant to this specific persona. Use the definitions and examples below.

---

📌 DEFINITION OF "RELEVANT":

A capability blueprint is considered "relevant" to a persona **only if** the persona is expected to:
- Directly use or interact with the feature, OR
- Depend on it to complete a goal or overcome a challenge, OR
- Benefit meaningfully from it in their daily context

It is **not relevant** if:
- The persona is not responsible for it
- The functionality belongs to another user group
- It doesn't align with the persona information, (e.g., their goals, responsibilities, needs, main tasks, etc.)

---

📌 OUTPUT:

If relevant:
- Justify why this capability blueprint matters to this persona — in 1–3 sentences — using evidence from the persona information (e.g., needs, traits, goals, context, challenges, etc.).

If not relevant:
- Explain briefly (1–3 sentences) why not, based on the persona's role or lack of connection to the feature.
  
---

📤 JSON OUTPUT FORMAT:
{{
  "relevant": true or false,
  "justification": "..."
}}

---

💡 EXAMPLE ONLY (Do not mimic blindly):

- Example 1 — Relevant

    + Persona: Volunteer Event Organizer:
{{
  "Id": "P-000",
  "Name": "Linda Green",
  "Role": "Independent Retiree",
  "Tagline": "I enjoy living alone but rely on digital tools for small daily tasks.",
  "Core goals": ["Maintain independence", "Stay socially active"],
  "Typical challenges": ["Mild forgetfulness", "Discomfort using complex interfaces"],
  ...
}}

    + Capability Blueprint:
- Title: "Natural Interaction for Daily Living Support"
- Pillar: "Pillar 1 - User-Driven Interaction Assistant"

    + Result:
{{
  "relevant": true,
  "justification": "Linda's goal to maintain independence and her mild forgetfulness make natural interaction tools directly beneficial for her. A system that supports simple, voice-based task management would ease her daily routine without introducing interface complexity."
}}

    + Explanation: The blueprint directly supports Linda’s desire for independent living and compensates for her memory challenges, especially given her discomfort with complex interfaces.


- Example 2 — Not Relevant

    + Persona: Healthcare App Developer
{{
  "Id": "P-999",
  "Name": "James Brown",
  "Role": "Healthcare Application Developer",
  "Tagline": "I build secure, scalable backend systems for health platforms.",
  "Core goals": ["Ensure platform extensibility", "Maintain compliance with data standards"],
  "Typical challenges": ["Keeping up with integration requirements", "Supporting multi-device APIs"],
  ...
}}

    + Capability Blueprint:
- Title: "Personalized Cognitive Stimulation Activities"
- Pillar: "Pillar 4 - Physical & Cognitive Impairments Prevention"

    + Result:
{{
  "relevant": false,
  "justification": "James’s work focuses on backend infrastructure and integration rather than end-user content like cognitive exercises. The capability blueprint does not align with his goals or responsibilities."
}}

    + Explanation: This capability targets end-user interaction, which is completely unrelated to James’s backend development role.

⚠️ NOTE: These are just demonstrations for guidance. The examples above are to **help you understand the format** and level of reasoning expected.  Do not copy them 100% directly, as your analysis must be based on the specific persona and Capability Blueprint given.

Last, but not least, strictly, do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""

def build_suboption_matching_prompt(persona, cb, alfred_summary, group_summary) -> str:
    return f"""
You are a system analyst helping to align system capabilities with user needs in the ALFRED project.

--- ALFRED SYSTEM SUMMARY ---
{alfred_summary}

--- USER GROUP CONTEXT ---
{group_summary}

--- PERSONA ---
{persona.to_prompt_string()}

--- CAPABILITY BLUEPRINT TO ANALYZE ---
Title: "{cb['title']}"
Pillar: "{cb['pillar']}"
SubOptions:
{json.dumps(cb.get("subOptions", []), indent=2)}

Your task: Given that the capability blueprint's title has already been relevant to the given persona. Now, from the provided subOptions, choose the **most relevant** for this persona and justify your choice. If none of the subOptions match the persona's needs, return null. If you can find an option, please suggest a new title, and priotize it based on the persona information in the context of ALFRED system

---

📌 OUTPUT:

---

If relevant:
- Choose the most appropriate **subOption** (the one that aligns best with this persona's information (e.g., needs, traits, goals, context, challenges, etc.)).
- Justify why this capability blueprint's subOption matters to this persona — in 1–3 sentences — using evidence from the persona's information (e.g., needs, traits, goals, context, challenges, etc.).
- Suggest a revised title, by **combining the main title and chosen subOption** appropriately based on the given persona's information. Please do not just follow the format <oldTitle> - <chosenSubOption>, make sure they are combined reasonably, but the new title is still concise, specific, and relevant to the capability blueprint and the persona. If the original capability blueprint is broadly applicable, but not phrased in a way that suits this persona, suggest a modified version of the title that better fits the persona’s perspective. Leave it empty if not needed (e.g., No Capability Blueprint;s subOptions is not relevant to persona). Remain it the same if you don't want to change the title, but this is not likely to happen.
- Assign a priority from 1–5 based **only** on the persona’s context. See below for rules: Use the number only (1-5) (For example: `"priority": "3"` — do not use words like "High", "Low", or "Medium", do not include any additional text or commentary, and do NOT use any markdown, bold, italic, or special formatting in your response), where:
  1 = Very high priority. Will be implemented.
  2 = High priority. Important for the ALFRED system; an implementation is planned.
  3 = Normal priority. Will be implemented if resources are available.
  4 = Low priority. Only considered if synergies with other stories exist.
  5 = Out of scope. Will not be implemented.
  
If not relevant:
- Explain briefly (1–3 sentences) why not, based on the persona's role or lack of connection to the feature.
- Leave suggestedTitle empty.
- Leave subOption empty.
- Set priority to 5 (irrelevant/out of scope).

---

📤 JSON OUTPUT FORMAT:
{{
  "relevant": true or false,
  "chosenSubOption": "...",      // leave empty if none match
  "justification": "...",
  "suggestedTitle": "...",       // may revise the title or leave as is
  "priority": "1"                // must be a string between "1" and "5"
}}

---

💡 EXAMPLE ONLY (Do not mimic blindly):

- Example 1 — Relevant Title + Matching SubOption

    + Persona: Volunteer Event Organizer:
{{
  "Id": "P-000",
  "Name": "Linda Green",
  "Role": "Independent Retiree",
  "Tagline": "I enjoy living alone but rely on digital tools for small daily tasks.",
  "Core goals": ["Maintain independence", "Stay socially active"],
  "Typical challenges": ["Mild forgetfulness", "Discomfort using complex interfaces"],
  ...
}}

    + Capability Blueprint:
- Title: "Natural Interaction for Daily Living Support"
- Pillar: "Pillar 1 - User-Driven Interaction Assistant"
- SubOptions:
  + "Voice-controlled reminders and calendar",
  + "Simple language interface for task management",
  + "Touch-free device interaction",
  + "Daily summary reports via voice"
  
    + Result:
{{
  "relevant": true,
  "chosenSubOption": "Voice-controlled reminders and calendar",
  "justification": "...",
  "suggestedTitle": "Natural Interaction for Daily Living – Voice-Controlled Reminders and Calendar",
  "priority": "1"
}}

    + Explanation: This blueprint aligns well with Linda’s need for independence and minimal tech friction. Among the subOptions, voice-controlled reminders stand out as the most effective for addressing her forgetfulness in a low-effort way.
    
- Example 2 - Relevant Title, But No Matching SubOption

    + Persona: Compliance Officer for Digital Health
{{
  "Id": "P-013",
  "Name": "Rebecca Li",
  "Role": "Compliance Lead in Digital Health Innovation",
  "Tagline": "I ensure healthcare platforms meet international regulatory and privacy standards.",
  "Core goals": ["Ensure regulatory compliance", "Improve transparency in data handling"],
  "Typical challenges": ["Navigating fragmented data policies", "Lack of visibility into third-party system integrations"],
  ...
}}

    + Capability Blueprint:
- Title: "Multi-User Activity Monitoring"
- Pillar: "Pillar 3 - Effective & Personalized Care"
- SubOptions:
  + "Real-time caregiver alerts for activity deviation"
  + "Elder-to-elder activity comparison for motivation"
  + "Suggested routines based on group behavior"
  
    + Result:
{{
  "relevant": false,
  "chosenSubOption": null,
  "justification": "Although the title suggests value in observing user behavior, all listed subOptions are tailored for caregivers or end-users. Rebecca's work focuses on backend compliance, not on user activity or behavioral features.",
  "suggestedTitle": "",
  "priority": "5"
}}

    + Explanation: The capability blueprint's title may seem relevant at first, but none of its subOptions relate to regulatory compliance or data governance, which are Rebecca’s core priorities.

---

⚠️ NOTE: These are just demonstrations for guidance. The examples above are to **help you understand the format** and level of reasoning expected.  Do not copy them 100% directly, as your analysis must be based on the specific persona and Capability Blueprint given.

Last, but not least, strictly, do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""


def analyze_capability_blueprints(persona_loader: UserPersonaLoader):
    os.makedirs(FILTERED_CAPABILITY_BLUEPRINTS_DIR, exist_ok=True)

    # Step 1: Determine missing personas (whose JSON files do NOT exist yet)
    expected_files = {f"{persona.id}_capability_blueprints.json" for persona in persona_loader.personas}
    actual_files = set(os.listdir(FILTERED_CAPABILITY_BLUEPRINTS_DIR))
    missing_files = expected_files - actual_files
    missing_personas = [p for p in persona_loader.personas if f"{p.id}_capability_blueprints.json" in missing_files]

    if not missing_personas:
        print("✅ All filtered capability blueprint JSON files already exist. Skipping analysis.")
    else:
        print(f"📊 Generating filtered capability blueprints for {len(missing_personas)} missing personas...")

        alfred_summary = load_alfred_summary()
        capability_blueprint_loader = CapabilityBlueprintLoader()

        for persona in missing_personas:
            persona_id = persona.id
            user_group = persona.user_group
            group_key = user_group.lower().replace(" ", "_")

            try:
                group_summary = load_user_group_summary(group_key)
            except Exception as e:
                print(f"❌ Failed to load summary for {user_group}: {e}")
                continue

            analyzed_results = []
            for pillar in PILLARS:
                capability_blueprints = capability_blueprint_loader.get_by_user_group_and_pillar(user_group, pillar)
                if not capability_blueprints:
                    continue

                for cb in capability_blueprints:
                    # Step 1: Check relevance
                    relevance_prompt = build_relevance_prompt(persona, cb, alfred_summary, group_summary)
                    relevance_response = get_llm_response(relevance_prompt)

                    try:
                        relevance_result = json.loads(relevance_response)
                        if not relevance_result.get("relevant", False):
                            print(f"⏭️ Skipping {cb['id']} for {persona_id} — not relevant (title)")
                            continue
                    except Exception as e:
                        print(f"⚠️ Relevance check error for {persona_id} - {cb['id']}: {e}")
                        continue

                    # Step 2: SubOption matching
                    suboption_prompt = build_suboption_matching_prompt(persona, cb, alfred_summary, group_summary)
                    suboption_response = get_llm_response(suboption_prompt)

                    if not suboption_response or suboption_response.strip().lower() == "null":
                        print(f"⚠️ Skipping {cb['id']} for {persona_id} — LLM returned null")
                        continue

                    try:
                        match_result = json.loads(suboption_response)
                        if not match_result.get("relevant", False):
                            print(f"⏭️ Skipping {cb['id']} for {persona_id} — no relevant subOption")
                            continue

                        sub = match_result.get("chosenSubOption", "")
                        if not sub:
                            print(f"⏭️ No subOption selected for {cb['id']} / {persona_id}")
                            continue

                        enriched_result = {
                            "personaId": persona_id,
                            "cbId": cb["id"],
                            "title": match_result.get("suggestedTitle", cb["title"]),
                            "pillar": cb["pillar"],
                            "priority": match_result.get("priority", "3"),
                            "userGroup": cb["userGroup"],
                            "justification": match_result.get("justification", ""),
                            "subOption": sub
                        }
                        analyzed_results.append(enriched_result)

                    except Exception as e:
                        print(f"⚠️ SubOption matching error for {persona_id} - {cb['id']}: {e}")

            # Save results for this persona
            output_path = os.path.join(FILTERED_CAPABILITY_BLUEPRINTS_DIR, f"{persona_id}_capability_blueprints.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(analyzed_results, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(analyzed_results)} capability blueprints for {persona_id}")

    # Step 2: Generate CSV summaries (even if JSONs were already there)
    capability_blueprint_loader = CapabilityBlueprintLoader()
    os.makedirs(FILTERED_CAPABILITY_BLUEPRINT_SUMMARIES_DIR, exist_ok=True)

    for user_group in set(p.user_group for p in persona_loader.personas):
        group_key = USER_GROUP_KEYS[user_group]
        summary_filename = f"{group_key}_capability_blueprint_summary.csv"
        summary_path = os.path.join(FILTERED_CAPABILITY_BLUEPRINT_SUMMARIES_DIR, summary_filename)

        if os.path.exists(summary_path):
            print(f"✅ CSV summary already exists for '{user_group}'. Skipping.")
        else:
            print(f"📄 Generating CSV summary for '{user_group}'...")
            generate_capability_blueprint_csv_summary(capability_blueprint_loader, user_group)
            

def generate_capability_blueprint_csv_summary(loader: CapabilityBlueprintLoader, user_group: str):
    """
    Generates a CSV summary of capability blueprint selections for each persona in a user group.

    Output: CSV saved to FILTERED_CAPABILITY_BLUEPRINT_SUMMARIES_DIR/<user_group>_capability_blueprint_summary.csv
    """
    os.makedirs(FILTERED_CAPABILITY_BLUEPRINT_SUMMARIES_DIR, exist_ok=True)

    # Step 1: Load all capability blueprints for this user group
    group_cb = loader.get_by_user_group(user_group)

    # Step 2: Load filtered CBs for personas in this user group
    persona_cb_map = {}
    for fname in os.listdir(FILTERED_CAPABILITY_BLUEPRINTS_DIR):
        if not fname.endswith(".json"):
            continue

        fpath = os.path.join(FILTERED_CAPABILITY_BLUEPRINTS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not data or data[0]["userGroup"] != user_group:
                continue
            persona_id = data[0]["personaId"]
            persona_cb_map[persona_id] = {entry["cbId"]: entry["subOption"] for entry in data}
        except Exception as e:
            print(f"⚠️ Failed to load or parse {fname}: {e}")
            continue

    # Step 3: Generate summary table
    rows = []
    for cb in group_cb:
        row = {
            "CB ID": cb["id"],
            "CB Title": cb["title"],
            "Pillar": cb["pillar"]
        }
        for persona_id in sorted(persona_cb_map.keys()):
            selected_option = persona_cb_map[persona_id].get(cb["id"], "")
            row[f"{persona_id}_Chosen"] = "✅" if selected_option else "❌"
            row[f"{persona_id}_SubOption"] = selected_option
        rows.append(row)

    # Step 4: Export CSV
    df = pd.DataFrame(rows)
    df.sort_values(by=["Pillar", "CB ID"], inplace=True)

    output_path = os.path.join(
        FILTERED_CAPABILITY_BLUEPRINT_SUMMARIES_DIR,
        f"{user_group.replace(' ', '_')}_capability_blueprint_summary.csv"
    )
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"📄 Summary saved to: {output_path}")