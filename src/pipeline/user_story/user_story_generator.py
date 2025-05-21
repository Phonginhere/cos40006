import os
import json

from pathlib import Path

from pipeline.user_story.user_story_loader import UserStoryLoader
from pipeline.use_case.use_case_loader import UseCaseLoader
from pipeline.utils import (
    UserPersonaLoader,
    Utils,
)

def generate_complete_user_stories(persona_loader: UserPersonaLoader, use_case_loader: UseCaseLoader):
    utils = Utils()

    # Load personas
    all_personas = {p.id: p for p in persona_loader.get_personas()}
    
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
    
    # Load invalid user story directory
    invalid_dir = Path(utils.DUPLICATED_USER_STORY_DIR_PATH)
    invalid_dir.mkdir(parents=True, exist_ok=True)
    
    # Load use cases
    use_case_loader.load()
    all_use_cases = {uc.id: uc for uc in use_case_loader.get_all()}
    
    # Load supporting documents
    system_summary = utils.load_system_context()
    story_guidelines = utils.load_user_story_guidelines()

    # Reload to ensure clean state
    loader = UserStoryLoader()
    loader.load_all_user_stories()

    # Filter incomplete stories
    incomplete_stories = [
        story for story in loader.get_all()
        if not story.title or not story.summary or story.priority is None or not story.pillar
    ]

    print(f"🛠️ Generating {len(incomplete_stories)} user stories with LLM...")
    
    # Load user group keys
    user_group_keys = utils.load_user_group_keys()
    
    # Load LLM response language proficiency level
    proficiency_level = utils.load_llm_response_language_proficiency_level()

    # Generate user stories' titles and summaries using LLM
    for story in incomplete_stories:
        persona = all_personas.get(story.persona)
        use_case = all_use_cases.get(story.use_case)
        group_key = user_group_keys.get(persona.user_group)
        group_summary = utils.load_user_group_description(group_key) if group_key else "Unknown"

        if not persona or not use_case:
            print(f"⚠️ Skipping US {story.id} (missing persona or use case)")
            continue
        
        previous_summaries = [
            s.summary for s in loader.get_by_persona(story.persona)
            if s.summary and s.id != story.id
        ]
        
        prev_summary_text = "\n".join(f"- {s}" for s in previous_summaries) if previous_summaries else "(None yet)"

        prompt = f"""
You are a Requirement Engineer, helping define detailed user stories for a system mentioned below. Below is the system overview, user story schema, user group needs, persona, related use case, and the raw task that **probably** inspired the user story.

--- SYSTEM OVERVIEW ---
{system_summary}
-------------------------------------------------------------

--- USER STORY GUIDELINES ---
{story_guidelines}
-------------------------------------------------------------

--- USER GROUP CONTEXT ({persona.user_group}) ---
{group_summary}
-------------------------------------------------------------

--- PERSONA DETAIL (ID: {persona.id}) ---
{persona.to_prompt_string()}
-------------------------------------------------------------

--- USE CASE DETAIL (ID: {use_case.id}
Description: {use_case.description}
Scenario: {use_case.scenario}
-------------------------------------------------------------

--- RAW TASK (Inspiration) ---
{story.task}
-------------------------------------------------------------

--- PREVIOUS SUMMARIES FOR THIS PERSONA ---
{prev_summary_text}
-------------------------------------------------------------

--- YOUR JOB ---
📌 Based on this information, generate a structured JSON for a meaningful user story. It can focus on either:
→ A functional intent (user’s goal, command, or system response)  
→ Or a system quality (privacy, simplicity, autonomy, responsiveness, personalization, etc.)

Generate the following fields:
- title
- summary
- priority (1 to 5)
- pillar (choose the most relevant system's pillar mentioned in the system summary among the provided in the relevant use case.")
-------------------------------------------------------------

--- INSTRUCTION ---
Your job is to generate a complete user story that reflects either:
- Behavioral (or functional) goals (e.g., what the user wants the system to do), or
- Quality/constraint-focused (or Non-Functional) goals (e.g., how the system should behave, qualities like performance, privacy, usability, ...).
(However, for this round, you will not classify them as functional or non-functional, or put these terms directly in the story)

However:
- You must NOT reuse the ideas already used in this persona’s previous user stories (listed below).
- If all of the persona’s information (e.g., goals, characteristics, challenges, singularities, main actions) has already been exhausted in those previous stories and you cannot write a new, meaningful story, return only an empty string ("") for the `summary` field.

Additionally:
- Only explore one, or (hardly) two, distinct ideas from the persona’s characteristics when generating the summary.
- You should still prioritize the persona’s perspective over consistency with system behavior.

Again, strictly, the new user story (especially the summary) must be strongly shaped by the given persona's information (e.g., unique needs, expectations, goals, characteristics, habits, concerns, ...) — even if this leads to inconsistencies with the use case or system description.
That is, the user story should be **persona-centric** and do not make it too "rational-based-on-the-system" or system-centric.
--------------------------------------------------------------

--- OUTPUT FORMAT ---
You must return a single JSON object with the following structure:

{{
  "title": "(User Story Title)",
  "summary": ""As a [user role, not name], I want to [do something specific] (, so that I can [achieve a goal or handle a concern].)", # "so that ..." is hardly optional
  "priority": 3, # 1 (Lowest) to 5 (Highest)
  "pillar": "(Associated Pillar)"
}}

Strictly, do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
------------------------------

{proficiency_level}

--- END OF PROMPT ---
"""

        try:
            response = utils.get_llm_response(prompt)
            json_data = json.loads(response)

            title = json_data.get("title", "")
            summary = json_data.get("summary", "")
            priority = json_data.get("priority")
            pillar = json_data.get("pillar")

            if not summary or str(summary).strip().lower() in ["", "none", "null"]:
                raise ValueError("Summary is missing or empty")

            story.title = title
            story.summary = summary
            story.priority = priority
            story.pillar = pillar

            print(f"✅ Story {story.id} created: {title} → {summary[:40]}...")

        except Exception as e:
            # Move invalid story to invalid folder
            # invalid_file = invalid_dir / f"Invalid_user_stories_for_{story.persona}.json"
            # try:
            #     existing = []
            #     if invalid_file.exists():
            #         with open(invalid_file, "r", encoding="utf-8") as f:
            #             existing = json.load(f)
            #     existing.append(story.to_dict())
            #     with open(invalid_file, "w", encoding="utf-8") as f:
            #         json.dump(existing, f, indent=2, ensure_ascii=False)
            #     print(f"❌ Moved invalid story {story.id} → {invalid_file.name} (Reason: {str(e)})")
            # except Exception as write_err:
            print(f"❌ Failed to save invalid story {story.id}: {e}")

    # Save updated stories back to their respective files
    loader.save_all_user_stories_by_persona()

    print(f"✅ Finished updating {len(incomplete_stories)} user stories.")