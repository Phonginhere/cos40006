import os
import re
import json
from typing import Dict
from utils import get_llm_response, load_alfred_summary, load_user_group_summary, CURRENT_LLM

# Constants
PILLAR_KEYS = [
    ("Pillar 1 - User-Driven Interaction Assistant", "pillar_1_user_stories.json"),
    ("Pillar 2 - Personalized Social Inclusion", "pillar_2_user_stories.json"),
    ("Pillar 3 - Effective & Personalized Care", "pillar_3_user_stories.json"),
    ("Pillar 4 - Physical & Cognitive Impairments Prevention", "pillar_4_user_stories.json"),
    ("General Requirements", "general_user_stories.json"),
]

def build_user_story_prompt(persona, usecase_descriptions, req, pillar_name, user_group, usecase_ids, alfred_summary):
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

⚠️ IMPORTANT: The persona information provided below is the **primary and dominant source** for generating this story. Your response should reflect the specific needs, goals, context, and challenges of this persona. The raw requirement should serve only as a **general seed or inspiration**, not the core of the user story.
### Persona:
{json.dumps({
    "Id": persona.id,
    "Name": persona.name,
    "Role": persona.role,
    "Tagline": persona.tagline,
    "Demographic data": persona.demographic_data,
    "Core goals": persona.core_goals,
    "Typical challenges": persona.typical_challenges,
    "Singularities": persona.singularities,
    "Working situation": persona.working_situation,
    "Place of work": persona.place_of_work,
    "Expertise": persona.expertise,
    "Main tasks with system support": persona.main_tasks,
    "Most important tasks": persona.most_important_tasks,
    "Least important tasks": persona.least_important_tasks,
    "Miscellaneous": persona.miscellaneous
}, indent=2)}

### Use Cases Associated with this Persona:
{chr(10).join(usecase_descriptions)}

### Raw Requirement:
Title: {req['title']}
Nominated Priority (This might be changed in your response based on the inputted persona): {req['priority']}

### Task:
If the requirement is clearly relevant and beneficial to this persona, generate one user story using this format:

{{
  "title": "...",
  "summary": "As a [role], I want ... so that ...",
  "priority": "2",
  "pillar": "...",
  "userGroup": "...",
  "personaId": "P-...",
  "useCases": ["UC...", "UC...", ...],
}}

### Example User Story, created from the user persona from group "Developers and App Creators", with the role "developer". DO NOT rely 100% on this example. This is just to help you understand the format and level of detail expected in the output. The user stories should be based on the user group summary (as specified above), ALFRED system summary, the persona information, the use cases associated, e.t.c, you’ve been provided, and they should reflect the specific needs of the given Persona in relation to the ALFRED system.)::
{{
  "title": "Usability",
  "summary": "As a developer, I need an easy way to define questions (or actions) the user can ask and perform.",
  "priority": "1",
  "pillar": "Pillar 1 - User-Driven Interaction Assistant",
  "userGroup": "Developers and App Creators",
  "personaId": "P-001",
  "useCases": ["UC4.1"],
}}

If the requirement does not apply or is inconsistent with the persona, return only:
null

Strictly, do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""


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


def generate_user_stories_by_persona(persona_loader, usecase_loader):
    alfred_summary = load_alfred_summary()
    output_root = os.path.join("results", CURRENT_LLM, "user_stories")
    os.makedirs(output_root, exist_ok=True)

    group_key_map = {
        "Older Adults": "older_adults_user_stories",
        "Caregivers and Medical Staff": "caregivers_and_medical_staff_user_stories",
        "Developers and App Creators": "developers_and_app_creators_user_stories"
    }

    story_counter = 1

    for persona in persona_loader.personas:
        user_group = persona.classify_user_group()
        print(f"📌 Persona {persona.id} ({persona.name}) → User Group: {user_group}")

        group_folder = group_key_map.get(user_group)
        if not group_folder:
            print(f"⚠️ Unknown user group for {persona.id}. Skipping.")
            continue

        # Load filtered raw requirements
        requirement_path = os.path.join(
            "results", CURRENT_LLM, "filtered_raw_requirements", f"{persona.id}_raw_requirements.json"
        )

        if not os.path.exists(requirement_path):
            print(f"⚠️ Filtered requirements missing for {persona.id}. Skipping.")
            continue

        with open(requirement_path, "r", encoding="utf-8") as f:
            filtered_requirements = json.load(f)

        # Group requirements by pillar
        requirements_by_pillar: Dict[str, list] = {key: [] for key, _ in PILLAR_KEYS}
        for req in filtered_requirements:
            if req["pillar"] in requirements_by_pillar:
                requirements_by_pillar[req["pillar"]].append(req)

        # Get use cases associated with the persona
        associated_usecases = [
            uc for uc in usecase_loader.use_cases if persona.id in (uc.personas or [])
        ]
        usecase_ids = [uc.id for uc in associated_usecases]
        usecase_descriptions = [f"{uc.name}: {uc.description}" for uc in associated_usecases]

        # Persona output path
        persona_output_dir = os.path.join(output_root, group_folder, f"{persona.id}_user_stories")
        os.makedirs(persona_output_dir, exist_ok=True)

        for pillar_name, file_name in PILLAR_KEYS:
            user_stories = []
            raw_reqs = requirements_by_pillar.get(pillar_name, [])

            for req in raw_reqs:
                prompt = build_user_story_prompt(
                    persona, usecase_descriptions, req, pillar_name, user_group, usecase_ids, alfred_summary
                )
                response = get_llm_response(prompt)

                if response and response.strip().lower().strip('"') != "null":
                    try:
                        response_cleaned = safe_clean_response(response)
                        story = json.loads(response_cleaned)

                        # Assign ID and fix fields
                        story["id"] = f"US-{story_counter:03d}"
                        story["personaId"] = persona.id
                        story["rawRequirementId"] = req["reqId"]
                        story["useCases"] = usecase_ids
                        story["pillar"] = pillar_name
                        story["userGroup"] = user_group
                        story_counter += 1

                        user_stories.append(story)

                    except json.JSONDecodeError:
                        print(f"⚠️ JSON parse error for {persona.id} / {req['reqId']}")
                        print("Raw:", response)

            if user_stories:
                path = os.path.join(persona_output_dir, file_name)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(user_stories, f, indent=2, ensure_ascii=False)