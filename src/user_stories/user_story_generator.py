import os
import json

from utils import (
    load_alfred_summary,
    load_user_story_summary,
    load_user_group_summary,
    get_llm_response,
    USER_STORY_DIR,
    USER_GROUP_KEYS
)

from user_stories.user_story_loader import UserStoryLoader
from user_persona_loader import UserPersonaLoader
from use_cases.use_case_loader import UseCaseLoader

def generate_complete_user_stories(persona_loader: UserPersonaLoader, use_case_loader: UseCaseLoader):
    # Load supporting documents
    alfred_summary = load_alfred_summary()
    story_summary = load_user_story_summary()
    
    # Load use cases and personas
    persona_loader.load()
    all_personas = {p.id: p for p in persona_loader.get_personas()}
    use_case_loader.load()
    all_use_cases = {uc.id: uc for uc in use_case_loader.get_all()}
    
    # Step Skipping Logic – check if all stories are fully generated
    loader = UserStoryLoader()
    loader.load_all_user_stories()
    all_stories = loader.get_all()

    persona_ids = set(p.id for p in all_personas.values())
    complete_personas = {
        pid for pid in persona_ids
        if all(story.title and story.summary for story in loader.get_by_persona(pid))
    }

    if complete_personas == persona_ids:
        print(f"⏭️ Skipping generation: All user stories for {len(persona_ids)} personas are complete (title and summary filled).")
        return
    
    # Load all user stories
    loader = UserStoryLoader()
    loader.load_all_user_stories()

    # Process only skeletons (missing title and summary)
    incomplete_stories = [story for story in loader.get_all() if not story.title or not story.summary]

    print(f"🛠️ Generating {len(incomplete_stories)} user stories with LLM...")

    for story in incomplete_stories:
        persona = all_personas.get(story.persona)
        use_case = all_use_cases.get(story.use_case)
        group_key = USER_GROUP_KEYS.get(persona.user_group)
        group_summary = load_user_group_summary(group_key) if group_key else "Unknown"

        if not persona or not use_case:
            print(f"⚠️ Skipping US {story.id} (missing persona or use case)")
            continue

        prompt = f"""
You are a Requirement Engineer, helping define detailed user stories for a smart assistant system called ALFRED.

Your job is to generate complete user stories that reflect either:
- Behavioral (or functional) goals (e.g., what the user wants the system to do), or
- Quality/constraint-focused (or Non-Functional) goals (e.g., how the system should behave, qualities like performance, privacy, usability).
(But for this task, you will not classify them as functional or non-functional.)

Note that, in this round, **prioritize non-functional stories** where applicable (e.g., comfort, privacy, emotional well-being, interface clarity, autonomy, trust, etc.).
Functional stories are still allowed—but prefer quality-centric expectations that shape how ALFRED behaves or is perceived.

Below is the system overview, user story schema, user group needs, persona, related use case, and the raw task that inspired the user story.

--- ALFRED SYSTEM OVERVIEW ---
{alfred_summary}

--- ALFRED USER STORY DEFINITIONS, STRUCTURE, RULES & UNREAL EXAMPLES ---
{story_summary}

--- USER GROUP CONTEXT ({persona.user_group}) ---
{group_summary}

--- PERSONA DETAIL (ID: {persona.id}) ---
{persona.to_prompt_string()}

--- USE CASE DETAIL (ID: {use_case.id}) ---
Name: {use_case.name}
Type: {use_case.use_case_type}
Pillars: {", ".join(use_case.pillars)}
Personas: {", ".join(use_case.personas)}
Description: {use_case.description}
Scenario: {use_case.scenario}

--- RAW TASK (Inspiration) ---
{story.task}

📌 Based on this information, generate a structured JSON for a meaningful user story. It can focus on either:
→ A specific function the persona wants to achieve, OR  
→ A specific system characteristic, quality, or expectation (privacy, simplicity, feedback, accessibility, emotional fit, trust, etc.).

Generate the following fields:
- title
- summary
- priority (1 to 5)
- pillar (choose the most relevant ALFRED pillar among the provided in the relevant use case. Also, you can use "Core" if the persona is from the group "Developers and App Creators")

Note that, you must first prioritize these atributes based on the given persona details, followed by the use case details, and finally the system overview. The user story should be relevant to the persona's needs and the use case context.

--- OUTPUT FORMAT ---

You must return a single JSON object with the following structure:

{{
  "title": "User Story Title",
  "summary": "A brief summary of the user story.",
  "priority": 3, # 1 (Lowest) to 5 (Highest)
  "pillar": "Associated Pillar"
}}

Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""

        try:
            response = get_llm_response(prompt)
            json_data = json.loads(response)

            story.title = json_data.get("title", "")
            story.summary = json_data.get("summary", "")
            story.priority = json_data.get("priority")
            story.pillar = json_data.get("pillar")

        except Exception as e:
            print(f"❌ Failed to process story {story.id}: {e}")
            continue

    # Save updated stories back to their respective files
    loader.save_all_user_stories_by_persona()

    print(f"✅ Finished updating {len(incomplete_stories)} user stories.")