import json
import os
from typing import List
from utils import load_alfred_summary, get_llm_response, CURRENT_LLM
from use_case_loader import UseCaseLoader, UseCase
from user_persona_loader import UserPersonaLoader, UserPersona

# Define the output directory based on the CURRENT_LLM variable
OUTPUT_DIR = os.path.join("results", CURRENT_LLM, "use_cases")


# =========================================================
# Phase 1: Generate Raw Use Cases
# =========================================================

def build_use_case_prompt(system_summary: str) -> str:
    """
    Build the prompt for generating raw use cases for the ALFRED system.
    The prompt instructs the LLM to output a JSON array of use cases, each with:
    - id
    - pillar (one of 5: 4 ALFRED pillars + General Requirements)
    - name
    - description
    """
    return f"""
You are a system requirements engineer.

Below is the summary of a system called ALFRED:

--- ALFRED SYSTEM SUMMARY ---
{system_summary}
-----------------------------

Your task is to generate a list of universal, persona-agnostic use cases for the ALFRED system. These use cases define key system functionalities across five categories:

1. Pillar 1 - User-Driven Interaction Assistant  
   (e.g., voice commands for daily tasks, reminders, basic queries)

2. Pillar 2 - Personalized Social Inclusion  
   (e.g., helping older adults connect with others, receive activity suggestions)

3. Pillar 3 - Effective & Personalized Care  
   (e.g., health monitoring, integration with wearables, caregiver alerts)

4. Pillar 4 - Physical & Cognitive Impairments Prevention  
   (e.g., serious games, exercise tracking, mental stimulation activities)

5. General Requirements  
   These refer to cross-cutting or system-wide capabilities that:
   - Are not specific to one pillar
   - Support the whole ALFRED platform
   - Often include privacy, security, installation, customization, accessibility, and system integration

Each use case must:
- Include a unique ID in the format "UC-001", "UC-002", etc.
- Include a **pillar** name from one of the 5 categories above.
- Include a short but clear **name**.
- Include a brief **description** (1–3 sentences) to explain the goal and function of the use case.

Output format (JSON array) is given as the below example:
[
  {{
    "id": "UC-001",
    "pillar": "Pillar 3 - Effective & Personalized Care",
    "name": "Remind Medication Intake",
    "description": "Enable ALFRED to issue voice-based reminders to users when it’s time to take their prescribed medications, and confirm whether they have taken them."
  }},
  ...
]

Only output a valid JSON array. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""

def generate_raw_use_cases():
    # Load the ALFRED system summary
    print("📥 Loading ALFRED system summary...")
    system_summary = load_alfred_summary()
    
    # Build the prompt for use case generation
    print("💬 Building prompt for raw use cases...")
    prompt = build_use_case_prompt(system_summary)
    
    # Get the LLM response using your dispatcher
    print("🤖 Requesting raw use cases from LLM...")
    response = get_llm_response(prompt)
    
    if response:
        try:
            # Parse the JSON response
            use_cases = json.loads(response)
            print(f"✅ Generated {len(use_cases)} raw use cases.")
            
            # Ensure the output directory exists
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            
            # Save each use case as its own file
            os.makedirs(OUTPUT_DIR, exist_ok=True)

            for uc in use_cases:
                file_path = os.path.join(OUTPUT_DIR, f"{uc['id']}.json")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(uc, f, indent=2, ensure_ascii=False)
                print(f"📝 Saved {uc['id']}")

            print(f"💾 Saved {len(use_cases)} individual use case files to {OUTPUT_DIR}")
        except json.JSONDecodeError as e:
            print("❌ Failed to parse LLM response as JSON.")
            print("LLM Response:")
            print(response)
    else:
        print("❌ No valid response from LLM.")

# =========================================================
# Phase 2: Enrich Use Cases with Scenarios and Personas
# =========================================================

def summarize_persona_for_matching(persona: UserPersona) -> str:
    """Short summary of a persona used for relevance filtering."""
    return f"""
Id: {persona.id}
Name: {persona.name}
Role: {persona.role}
Core Goals: {', '.join(persona.core_goals[:2])}
Typical Challenges: {', '.join(persona.typical_challenges[:2])}
Context: {persona.working_situation}
""".strip()

def summarize_persona_for_scenario(persona: UserPersona) -> str:
    """Returns just the name of the persona for scenario generation."""
    return persona.name


def build_persona_matching_prompt(use_case: UseCase, persona_summaries: List[str]) -> str:
    return f"""
You are designing user stories for the ALFRED system.

Below is a use case:
ID: {use_case.id}
Pillar: {use_case.pillar}
Name: {use_case.name}
Description: {use_case.description}

Here are summaries of available user personas:
{''.join(['---\n' + ps + '\n' for ps in persona_summaries])}

Select one or more personas that are most relevant for participating in or supporting this use case. Return a JSON list of their **IDs** only. Base your selection on their roles, goals, and challenges.

Strictly respond in the following JSON format: (Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.)
["P-001", "P-004"]
"""

def build_scenario_prompt(use_case: UseCase, persona_names: List[str]) -> str:
    alfred_summary = load_alfred_summary()

    return f"""
You are writing a lifelike usage scenario for the ALFRED system.

--- ALFRED SYSTEM SUMMARY ---
{alfred_summary}
-----------------------------

Below is an example scenario. It is only for the use case "Effective and Personalized Care". The example is provided to show the tone, structure, and depth expected in your writing. **Do not rely on its content**.

---
Personas: Otto the Older Person and Mike from the Medical Staff

Scenario: 
Mike from the Medical Staff has been caring for Otto, an older adult with mildly high blood pressure. To improve Otto’s care and provide peace of mind, they decide to use the ALFRED system along with a smart shirt that tracks vital signs like heart rate, temperature, breathing, and activity. This data is shared with Mike through ALFRED, while Otto stays in control of what’s shared and can view his own stats. He appreciates the privacy settings and wants the shirt to look stylish, not medical. ALFRED also reminds him to take his pills, and he confirms once he has. Occasionally, Mike checks in via video call, ensuring Otto is doing well, especially since he doesn’t have much social interaction. Together, ALFRED helps maintain Otto’s independence while supporting more effective and personalized care.
---

Now, please generate a scenario for a different use case and its involved personas:

Use Case:
ID: {use_case.id}
Pillar: {use_case.pillar}
Name: {use_case.name}
Description: {use_case.description}

Involved Personas:
{', '.join(persona_names)}

Write a grounded, practical, human-centered scenario showing how these individuals interact with ALFRED to fulfill this use case. Be realistic and detailed — include motivations, interactions, day-to-day context, and outcomes.

Return only the scenario narrative. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""

def enrich_use_cases_with_scenarios():
    print("\n🔄 Phase 2: Enriching use cases with personas and scenarios...")

    # Load use cases
    use_case_loader = UseCaseLoader()
    use_case_loader.load()
    use_cases = use_case_loader.get_all()

    # Load personas
    persona_loader = UserPersonaLoader()
    persona_loader.load()
    all_personas = persona_loader.get_personas()
    persona_by_id = {p.id: p for p in all_personas}

    for use_case in use_cases:
        if use_case.scenario and use_case.personas:
            print(f"⏭️ Skipping {use_case.id} — already enriched.")
            continue

        print(f"✏️ Enriching {use_case.id}...")

        # Phase 2A: Find matching persona IDs via LLM
        persona_matching_summaries = [summarize_persona_for_matching(p) for p in all_personas]
        matching_prompt = build_persona_matching_prompt(use_case, persona_matching_summaries)
        persona_id_list = get_llm_response(matching_prompt)

        try:
            matched_ids = json.loads(persona_id_list)
        except json.JSONDecodeError:
            print(f"⚠️ Could not parse LLM response for persona matching in {use_case.id}. Using all personas.")
            matched_ids = [p.id for p in all_personas]

        use_case.personas = matched_ids

        # Phase 2B: Generate scenario using matched persona names
        matched_names = [persona_by_id[pid].name for pid in matched_ids if pid in persona_by_id]
        scenario_prompt = build_scenario_prompt(use_case, matched_names)
        scenario_text = get_llm_response(scenario_prompt)

        use_case.scenario = scenario_text or "Scenario could not be generated."

    # Save updated use cases back to disk
    use_case_loader.save_all()
    print("✅ Finished enriching all use cases.")
