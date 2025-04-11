import os
import json
from utils import get_llm_response, load_alfred_summary, load_user_group_summary, CURRENT_LLM
from raw_requirement_loader import RawRequirementLoader
from user_persona_loader import UserPersonaLoader

# Constants
OUTPUT_DIR = os.path.join("results", CURRENT_LLM, "filtered_raw_requirements")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_requirement_analysis_prompt(persona, req, alfred_summary, group_summary) -> str:
    return f"""
You are a system analyst helping to align system capabilities with user needs in the ALFRED project.

--- ALFRED SYSTEM OVERVIEW ---
{alfred_summary}

--- USER GROUP CONTEXT ---
{group_summary}

--- PERSONA OVERVIEW ---
{json.dumps(persona.to_dict(), indent=2)}

--- RAW REQUIREMENT TO ANALYZE ---
Title: "{req['title']}"
Pillar: "{req['pillar']}"

Your task:
Determine whether the above requirement is relevant to this specific persona. Use the definitions and examples below.

---

📌 DEFINITION OF "RELEVANT":

A raw requirement is considered "relevant" to a persona **only if** the persona is expected to:
- Directly use or interact with the feature, OR
- Depend on it to complete a goal or overcome a challenge, OR
- Benefit meaningfully from it in their daily context

It is **not relevant** if:
- The persona is not responsible for it
- The functionality belongs to another user group
- It doesn't align with their goals, responsibilities, or needs

---

📌 OUTPUT:

- "relevant": Boolean value. Should be true if the requirement is applicable to this persona’s goals, challenges, or work responsibilities. Otherwise, false.
- "justification": A concise explanation (1–3 sentences) of why the requirement is or isn't relevant — using evidence from the persona. This must include why it aligns or conflicts.
- "suggestedTitle" Optional string. If the original requirement is broadly applicable, but not phrased in a way that suits this persona, suggest a modified version of the title that better fits the persona’s perspective. Leave it empty if not needed (e.g., the raw requirement is not relevant to persona). Remain it the same if you don't want to change the title.

---

📌 OUTPUT FORMAT:

{{
  "relevant": true or false,
  "justification": "...",
  "suggestedTitle": "..."
}}

---

💡 EXAMPLE ONLY (Do not mimic blindly):

EXAMPLE 1:
Persona: Volunteer Event Organizer:
{{
  "Id": "P-000",
  "Name": "Peter Green",
  "Role": "Volunteer Event Organizer",
  "Tagline": "I help organize community events for seniors using digital tools.",
  "Core goals": ["Promote social events for older adults", "Streamline event planning"],
  "Typical challenges": ["Limited technical experience", "Scheduling conflicts"]
}}
Requirement: 
- Title: "Health Monitoring Dashboard for Real-Time Alerts"  
- Pillar: "Pillar 3 - Effective & Personalized Care"
Result:
{{
  "relevant": false,
  "justification": "This persona is focused on social event planning and has no medical monitoring responsibilities.",
  "suggestedTitle": ""
}}
Explanation: In the above example, the raw requirement title describes a medical monitoring feature. The persona, Daniel, works in event coordination, with no medical tasks or goals. Therefore, it is marked not relevant.
We do not suggest an alternative title, because the entire feature area is outside his responsibility.

EXAMPLE 2:
Persona:
{{
  "Id": "P-999",
  "Name": "James Brown",
  "Role": "Professional Caregiver",
  "Tagline": "I manage health and well-being of elderly clients across care facilities.",
  "Core goals": ["Monitor client health", "Coordinate care with families"],
  "Typical challenges": ["Limited time", "Need for quick access to vital data"]
}}
Requirement:
- Title: "Natural Language Command for Health Monitoring"
- Pillar: "Pillar 1 - User-Driven Interaction Assistant"
Result:
{{
  "relevant": true,
  "justification": "This requirement allows Sarah to access client health information via voice, aligning with her need for fast, hands-free interaction during busy care schedules.",
  "suggestedTitle": "Voice Commands for Client Health Checks"
}}
Explanation: In this case, the persona is a professional caregiver with time constraints and a goal to monitor health data. Using natural language commands helps her efficiently access critical information. This makes the requirement relevant. The suggested title reframes the functionality in terms that directly reflect her workflow.

---

⚠️ NOTE: These are just demonstrations for guidance. The examples above are to **help you understand the format** and level of reasoning expected.  Do not copy them 100% directly, as your analysis must be based on the specific persona and requirement given.
"""


def analyze_requirements():
    alfred_summary = load_alfred_summary()
    persona_loader = UserPersonaLoader()
    persona_loader.load()
    requirement_loader = RawRequirementLoader()

    for persona in persona_loader.personas:
        persona_id = persona.id
        user_group = persona.classify_user_group()
        group_key = user_group.lower().replace(" ", "_")

        try:
            group_summary = load_user_group_summary(group_key)
        except Exception as e:
            print(f"❌ Failed to load group summary for {user_group}: {e}")
            continue

        raw_requirements = requirement_loader.get_by_user_group(user_group)
        analyzed_results = []

        for req in raw_requirements:
            prompt = build_requirement_analysis_prompt(persona, req, alfred_summary, group_summary)
            
            result = get_llm_response(prompt)
            if not result or result.strip().lower() == "null":
                print(f"❌ Skipped {req['reqId']} for {persona_id} — response is null or empty")
                continue

            try:
                analysis = json.loads(result)
                if analysis.get("relevant") is True:
                    analyzed_results.append({
                        "personaId": persona_id,
                        "reqId": req["id"],
                        "title": analysis.get("suggestedTitle", req["title"]),
                        "pillar": req["pillar"],
                        "priority": req["priority"],
                        "userGroup": req["userGroup"],
                        "justification": analysis.get("justification", "")
                    })
            except Exception as e:
                print(f"⚠️ Error parsing response for {persona_id} - {req['reqId']}: {e}")

        output_path = os.path.join(OUTPUT_DIR, f"{persona_id}_raw_requirements.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analyzed_results, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(analyzed_results)} relevant requirements for {persona_id}")
