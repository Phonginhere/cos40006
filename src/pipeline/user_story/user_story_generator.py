import os
import json

from pipeline.user_story.user_story_loader import UserStoryLoader
from pipeline.user_persona_loader import UserPersonaLoader
from pipeline.use_case.use_case_loader import UseCaseLoader
from pipeline.utils import (
    load_system_summary,
    load_user_story_guidelines,
    load_user_group_guidelines,
    get_llm_response,
    USER_GROUP_KEYS
)

def generate_complete_user_stories(persona_loader: UserPersonaLoader, use_case_loader: UseCaseLoader):
    # Load supporting documents
    system_summary = load_system_summary()
    story_guidelines = load_user_story_guidelines()
    
    # Load use cases and personas
    all_personas = {p.id: p for p in persona_loader.get_personas()}
    use_case_loader.load()
    all_use_cases = {uc.id: uc for uc in use_case_loader.get_all()}
    
    # Step Skipping Logic – check if all stories are fully generated
    loader = UserStoryLoader()
    loader.load_all_user_stories()
    all_stories = loader.get_all()

    # Check if all user stories for each persona are complete
    persona_ids = set(p.id for p in all_personas.values())
    complete_personas = {
        pid for pid in persona_ids
        if all(
            story.title and story.summary and story.priority is not None and story.pillar
            for story in loader.get_by_persona(pid)
        )
    }

    if complete_personas == persona_ids:
        print(f"⏭️ Skipping generation: All user stories for {len(persona_ids)} personas are complete (title, summary, priority, and pillar filled).")
        return

    # Reload to ensure clean state
    loader = UserStoryLoader()
    loader.load_all_user_stories()

    # Filter incomplete stories
    incomplete_stories = [
        story for story in loader.get_all()
        if not story.title or not story.summary or story.priority is None or not story.pillar
    ]

    print(f"🛠️ Generating {len(incomplete_stories)} user stories with LLM...")

    # Generate user stories' titles and summaries using LLM
    for story in incomplete_stories:
        persona = all_personas.get(story.persona)
        use_case = all_use_cases.get(story.use_case)
        group_key = USER_GROUP_KEYS.get(persona.user_group)
        group_summary = load_user_group_guidelines(group_key) if group_key else "Unknown"

        if not persona or not use_case:
            print(f"⚠️ Skipping US {story.id} (missing persona or use case)")
            continue

        prompt = f"""
You are a Requirement Engineer, helping define detailed user stories for a system mentioned below.

Your job is to generate a complete user story that reflects either:
- Behavioral (or functional) goals (e.g., what the user wants the system to do), or
- Quality/constraint-focused (or Non-Functional) goals (e.g., how the system should behave, qualities like performance, privacy, usability).
(However, for this round, you will not classify them as functional or non-functional, or put these terms directly in the story)

Note that, when designing the story, you should lean **slightly** toward **functional** stories when plausible — especially those involving:
- Clear user actions, commands, or requests
- Interaction flows or task completions
- Decision-making, input/output, or system responsiveness
Use non-functional expectations when the persona’s behavior or the task **clearly emphasizes** a system quality.

Below is the system overview, user story schema, user group needs, persona, related use case, and the raw task that inspired the user story.

--- SYSTEM OVERVIEW ---
{system_summary}

--- GIVEN SYSTEM'S USER STORY DEFINITIONS, STRUCTURE, RULES & UNREAL EXAMPLES ---
{story_guidelines}

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
→ A functional intent (user’s goal, command, or system response)  
→ Or a system quality (privacy, simplicity, autonomy, responsiveness, personalization, etc.)

Generate the following fields:
- title
- summary
- priority (1 to 5)
- pillar (choose the most relevant system's pillar mentioned in the system summary among the provided in the relevant use case.")

--- STRICT INSTRUCTION ---

Strictly, the user story must be strongly shaped by the persona's unique needs, expectations, habits, and emotional concerns — even if this leads to inconsistencies with the use case or system description.
If the persona’s preferences clash with technical assumptions or systemic defaults, let that divergence emerge. Do NOT suppress conflicting expectations or overly rationalize differences for the sake of system alignment. 
Your story should prioritize the **persona’s reality over system ideals**. Realism, friction, and individuality are more valuable than architectural harmony.

--- OUTPUT FORMAT ---

You must return a single JSON object with the following structure:

{{
  "title": "User Story Title",
  "summary": ""As a [user role, not name], I want to [do something specific] (, so that I can [achieve a goal or handle a concern].)", # "so that ..." is hardly optional
  "priority": 3, # 1 (Lowest) to 5 (Highest)
  "pillar": "[Associated Pillar]"
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
            
            print(f"✅ Processed story {story.id}: {story.title} (Priority: {story.priority}, Pillar: {story.pillar})")

        except Exception as e:
            print(f"❌ Failed to process story {story.id}: {e}")
            continue

    # Save updated stories back to their respective files
    loader.save_all_user_stories_by_persona()

    print(f"✅ Finished updating {len(incomplete_stories)} user stories.")