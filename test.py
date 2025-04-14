import os
import json
from utils import get_llm_response, load_alfred_summary, load_user_group_summary, CURRENT_LLM, PILLARS, FILTERED_CAPABILITY_BLUEPRINTS_DIR
from capability_blueprint_loader import CapabilityBlueprintLoader
from user_persona_loader import UserPersonaLoader


def build_capability_blueprint_analysis_prompt(persona, cb, alfred_summary, group_summary) -> str:
    return f"""
You are a system analyst helping to align system capabilities with user needs in the ALFRED project.

--- ALFRED SYSTEM OVERVIEW ---
{alfred_summary}

--- USER GROUP CONTEXT ---
{group_summary}

--- PERSONA OVERVIEW ---
{persona.to_prompt_string()}

--- CAPABILITY BLUEPRINT TO ANALYZE ---
Title: "{cb['title']}"
Pillar: "{cb['pillar']}"
SubOptions:
{json.dumps(cb.get("subOptions", []), indent=2)}

Your task:
Determine whether the above capability blueprint is relevant to this specific persona. Use the definitions and examples below.

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
- The title of the capability blueprint is relevant to the persona, but no sub-options is suitable for it.

---

📌 OUTPUT:

If relevant:
- Choose the most appropriate **subOption** (the one that aligns best with this persona's needs, goals, and context).
- Justify why this capability blueprint (and subOption) matters to this persona — in 1–3 sentences — using evidence from their traits, goals, or challenges.
- Suggest a revised title, by **combining the main title and chosen subOption** effectively and efficiently. If the original capability blueprint is broadly applicable, but not phrased in a way that suits this persona, suggest a modified version of the title that better fits the persona’s perspective. Leave it empty if not needed (e.g., the Capability Blueprint is not relevant to persona). Remain it the same if you don't want to change the title.
- Assign a priority from 1–5 based **only** on the persona’s context (see below for rules).

If not relevant:
- Explain briefly (1–3 sentences) why not, based on the persona's role or lack of connection to the feature.
- Leave suggestedTitle empty.
- Leave subOption empty.
- Set priority to 5 (irrelevant/out of scope).

---

---

📊 PRIORITY SCALE: (Use the number only (1-5). For example: `"priority": "3"` — do not use words like "High", "Low", or "Medium". Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.), where:
  1 = Very high priority. Will be implemented.
  2 = High priority. Important for the ALFRED system; an implementation is planned.
  3 = Normal priority. Will be implemented if resources are available.
  4 = Low priority. Only considered if synergies with other stories exist.
  5 = Out of scope. Will not be implemented.
  
---

📤 JSON OUTPUT FORMAT:

{{
  "relevant": true or false,
  "chosenSubOption": "...",         // leave empty if irrelevant
  "justification": "...",
  "suggestedTitle": "...",
  "priority": "..."
}}

---

💡 EXAMPLE ONLY (Do not mimic blindly):

EXAMPLE 1:
Persona: Volunteer Event Organizer:
{{
  "Id": "P-000",
  "Name": "Linda Green",
  "Role": "Independent Retiree",
  "Tagline": "I enjoy living alone but rely on digital tools for small daily tasks.",
  "Core goals": ["Maintain independence", "Stay socially active"],
  "Typical challenges": ["Mild forgetfulness", "Discomfort using complex interfaces"]
}}
Capability Blueprint:
- Title: "Natural Interaction for Daily Living Support"
- Pillar: "Pillar 1 - User-Driven Interaction Assistant"
- SubOptions:
  + "Voice-controlled reminders and calendar",
  + "Simple language interface for task management",
  + "Touch-free device interaction",
  + "Daily summary reports via voice"
Result:
{{
  "relevant": true,
  "chosenSubOption": "Voice-controlled reminders and calendar",
  "justification": "Linda values independence but has occasional forgetfulness. Voice-controlled reminders directly help her manage daily routines without needing complex navigation.",
  "suggestedTitle": "Natural Interaction for Daily Living – Voice-Controlled Reminders and Calendar",
  "priority": "1"
}}
Explanation: Linda's persona emphasizes independence, routine support, and simplicity. Voice-based reminders address both her mild memory challenges and tech discomfort. Hence, the Capability Blueprint is highly relevant, with a customized title to reflect the exact subOption most helpful to her.

EXAMPLE 2:
Persona:
{{
  "Id": "P-999",
  "Name": "James Brown",
  "Role": "Healthcare Application Developer",
  "Tagline": "I build secure, scalable backend systems for health platforms.",
  "Core goals": ["Ensure platform extensibility", "Maintain compliance with data standards"],
  "Typical challenges": ["Keeping up with integration requirements", "Supporting multi-device APIs"]
}}
Capability Blueprint:
- Title: "Personalized Cognitive Stimulation Activities"
- Pillar: "Pillar 4 - Physical & Cognitive Impairments Prevention"
- SubOptions:
  + "Audio-based memory games for elderly users",
  + "Interactive puzzles to support mental agility",
  + "Daily trivia with adaptive difficulty",
  + "Multi-user collaborative brain exercises"
Result:
{{
  "relevant": false,
  "chosenSubOption": "",
  "justification": "James focuses on backend development and integration tasks. This Capability Blueprint targets end-user stimulation features with no direct relation to his role.",
  "suggestedTitle": "",
  "priority": "5"
}}
Explanation: James is a developer persona focused on infrastructure and integration, not on gameplay or end-user cognitive features. He does not interact with or depend on such content directly — thus, this Capability Blueprint is not relevant to him.

---

⚠️ NOTE: These are just demonstrations for guidance. The examples above are to **help you understand the format** and level of reasoning expected.  Do not copy them 100% directly, as your analysis must be based on the specific persona and Capability Blueprint given.

Last, but not least, strictly, do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""


def analyze_capability_blueprints(persona_loader: UserPersonaLoader):
    os.makedirs(FILTERED_CAPABILITY_BLUEPRINTS_DIR, exist_ok=True)
    
    alfred_summary = load_alfred_summary()
    capability_blueprint_loader = CapabilityBlueprintLoader()

    for persona in persona_loader.personas:
        persona_id = persona.id
        user_group = persona.user_group
        group_key = user_group.lower().replace(" ", "_")

        try:
            group_summary = load_user_group_summary(group_key)
        except Exception as e:
            print(f"❌ Failed to load group summary for {user_group}: {e}")
            continue

        analyzed_results = []

        for pillar in PILLARS:
            capability_blueprints = capability_blueprint_loader.get_by_user_group_and_pillar(user_group, pillar)
            if not capability_blueprints:
                continue

            for cb in capability_blueprints:
                prompt = build_capability_blueprint_analysis_prompt(persona, cb, alfred_summary, group_summary)
                result = get_llm_response(prompt)

                if not result or result.strip().lower() == "null":
                    print(f"⚠️ Skipped {cb['id']} for {persona_id} — response is null or empty")
                    continue

                try:
                    analysis = json.loads(result)

                    if analysis.get("relevant") is True:
                        enriched_result = {
                            "personaId": persona_id,
                            "cbId": cb["id"],
                            "title": analysis.get("suggestedTitle", cb["title"]),
                            "pillar": cb["pillar"],
                            "priority": int(analysis.get("priority", 3)),
                            "userGroup": cb["userGroup"],
                            "justification": analysis.get("justification", ""),
                            "subOption": analysis.get("chosenSubOption", "")
                        }
                        analyzed_results.append(enriched_result)

                except Exception as e:
                    print(f"⚠️ Error parsing response for {persona_id} - {cb.get('id', 'UNKNOWN')}: {e}")
                    continue

        # Save results for this persona
        output_path = os.path.join(FILTERED_CAPABILITY_BLUEPRINTS_DIR, f"{persona_id}_capability_blueprints.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analyzed_results, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(analyzed_results)} relevant capability blueprints for {persona_id}")