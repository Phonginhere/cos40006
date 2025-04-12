import os
import re
import json
from typing import Dict
from utils import get_llm_response, load_alfred_summary, load_user_group_summary, CURRENT_LLM
from user_persona_loader import UserPersonaLoader
from use_case_loader import UseCaseLoader

# Constants
PILLAR_KEYS = [
    ("Pillar 1 - User-Driven Interaction Assistant", "pillar_1_user_stories.json"),
    ("Pillar 2 - Personalized Social Inclusion", "pillar_2_user_stories.json"),
    ("Pillar 3 - Effective & Personalized Care", "pillar_3_user_stories.json"),
    ("Pillar 4 - Physical & Cognitive Impairments Prevention", "pillar_4_user_stories.json"),
    ("General Requirements", "general_user_stories.json"),
]

FINAL_USER_STORY_DIR = os.path.join("results", CURRENT_LLM, "user_stories")


def safe_clean_response(response: str) -> str:
    """
    Fix known issues from LLM-generated JSON:
    - Improperly quoted useCases (single quotes)
    - Unescaped inner double-quotes in summary fields
    """
    # Fix single quotes in useCases
    response = re.sub(
        r'"useCases"\s*:\s*\[([^\]]+)\]',
        lambda m: '"useCases": [' + ', '.join(['"' + x.strip().strip('\'"') + '"' for x in m.group(1).split(',')]) + ']',
        response
    )

    # Escape unescaped inner double quotes in summary fields (basic case)
    response = re.sub(
        r'"summary"\s*:\s*"([^"]*?)"([^",])',
        lambda m: f'"summary": "{m.group(1)}\\"{m.group(2)}',
        response
    )

    return response

def build_user_story_prompt(persona, req, pillar_name, user_group, alfred_summary):
    group_key_map = {
        "Older Adults": "older_adults",
        "Caregivers and Medical Staff": "caregivers_and_medical_staff",
        "Developers and App Creators": "developers_and_app_creators"
    }

    group_key = group_key_map.get(user_group)
    group_summary = load_user_group_summary(group_key) if group_key else "No summary available."

    return f"""
You are generating a user story for the ALFRED system. Here is the context:

### ALFRED System Summary:
{alfred_summary}

### User Group: {user_group}
{group_summary}

⚠️ IMPORTANT: The persona information provided below is the **primary and dominant source** for generating this user story. Your response should reflect all information (e.g., the specific needs, goals, context, challenges, etc.) of this persona. The raw requirement, or even alfred system context, userGroup, should serve only as a **general seed or inspiration**, not the core of the user story. Sometimes, the information given in raw requirement in the context of ALFRED system summary may not be compatible with the information of the persona, in this case, the persona must be prioritized and the ALFRED system need to be flexible for this. This is the core funcationality of user stories.
### Persona:
{persona.to_prompt_string()}

### Raw Requirement:
Title: {req['title']}
Pillar: {pillar_name} (This should be remained the same in your response)
Nominated Priority: {req['priority']} (This should also be remained the same in your response)

### Task: If the requirement is clearly relevant and beneficial to this persona, generate one user story using this format:

{{
  "title": "...",
  "summary": "As a [role], I want ... so that ...",
  "priority": 2,
  "pillar": "...",
  "userGroup": "...",
  "personaId": "P-...",
}}

### Example User Story, created from the user persona from group "Developers and App Creators", with the role "developer". DO NOT rely 100% on this example. This is just to help you understand the format and level of detail expected in the output. The user stories should be based on the user group summary (as specified above), ALFRED system summary, the persona information, the use cases associated, e.t.c, you’ve been provided, and they should reflect the specific needs of the given Persona in relation to the ALFRED system.)::
{{
  "title": "Usability",
  "summary": "As a developer, I need an easy way to define questions (or actions) the user can ask and perform.",
  "priority": 1,
  "pillar": "Pillar 1 - User-Driven Interaction Assistant",
  "userGroup": "Developers and App Creators",
  "personaId": "P-001"
}}

If the requirement does not apply or is inconsistent with the persona, return only:
null

Strictly, do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""

def build_use_case_match_prompt(alfred_summary, persona, story, usecases: list) -> str:
    return f"""
You are analyzing which use cases are relevant to a specific user story in the ALFRED system.

### ALFRED System Summary:
{alfred_summary}

--- Persona ---
{persona.to_prompt_string()}

--- User Story ---
{json.dumps(story, indent=2)}

--- Available Use Cases ---
{chr(10).join(f"- {uc.id}: {uc.name} — {uc.description}" for uc in usecases)}

TASK: Based on this persona and story, return a JSON array of **use case IDs** that clearly relate to the user story:

Example:
["UC-001", "UC-004"]

If you can't find any appropriate use cases among the above list, feel free to return an empty list, e.g., []

Strictly return a valid JSON array. No text, no formatting.
"""


def generate_user_stories_by_persona(persona_loader: UserPersonaLoader, usecase_loader: UseCaseLoader):
    print("\n📘 Generating full user stories (persona → story → use case)...")
    os.makedirs(FINAL_USER_STORY_DIR, exist_ok=True)
    alfred_summary = load_alfred_summary()
    story_counter = 1

    group_map = {
        "Older Adults": "older_adults_user_stories",
        "Caregivers and Medical Staff": "caregivers_and_medical_staff_user_stories",
        "Developers and App Creators": "developers_and_app_creators_user_stories"
    }

    for persona in persona_loader.personas:
        group_folder = group_map.get(persona.user_group)
        if not group_folder:
            print(f"⚠️ Unknown user group for {persona.id}. Skipping.")
            continue

        # Load filtered raw requirements
        req_path = os.path.join("results", CURRENT_LLM, "filtered_raw_requirements", f"{persona.id}_raw_requirements.json")
        if not os.path.exists(req_path):
            print(f"⚠️ Missing filtered requirements for {persona.id}. Skipping.")
            continue

        with open(req_path, "r", encoding="utf-8") as f:
            filtered_reqs = json.load(f)
            
        associated_usecases = [uc for uc in usecase_loader.use_cases if persona.id in (uc.personas or [])]

        output_dir = os.path.join(FINAL_USER_STORY_DIR, group_folder, f"{persona.id}_user_stories")
        os.makedirs(output_dir, exist_ok=True)

        stories_by_pillar: Dict[str, list] = {pillar: [] for pillar, _ in PILLAR_KEYS}

        for req in filtered_reqs:
            pillar_name = req["pillar"]
            prompt = build_user_story_prompt(persona, req, pillar_name, persona.user_group, alfred_summary)
            response = get_llm_response(prompt)

            if response and response.strip().lower() != "null":
                try:
                    cleaned = safe_clean_response(response)
                    story = json.loads(cleaned)

                    # Phase 2: Match use cases for this story
                    match_prompt = build_use_case_match_prompt(alfred_summary, persona, story, associated_usecases)
                    usecase_response = get_llm_response(match_prompt)
                    try:
                        matched_usecases = json.loads(usecase_response)
                        story["useCases"] = matched_usecases
                    except:
                        print(f"⚠️ Use case match parse failed for {persona.id}, using empty list.")
                        story["useCases"] = []
                            
                    story["id"] = f"US-{story_counter:03d}"
                    story["personaId"] = persona.id
                    story["rawRequirementId"] = req["reqId"]
                    story["useCases"] = matched_usecases
                    story["pillar"] = pillar_name
                    story["userGroup"] = persona.user_group
                    story_counter += 1

                    stories_by_pillar[pillar_name].append(story)

                except json.JSONDecodeError:
                    print(f"⚠️ Story parse failed for {persona.id} - {req['reqId']}")
                    print(response)

        for pillar, filename in PILLAR_KEYS:
            if stories_by_pillar[pillar]:
                with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                    json.dump(stories_by_pillar[pillar], f, indent=2)
        print(f"✅ Saved stories for {persona.id} in {group_folder}")