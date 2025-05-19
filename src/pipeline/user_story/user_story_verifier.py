import os
import json

from pipeline.user_story.user_story_loader import UserStoryLoader
from pipeline.utils import Utils


def verify_user_stories(persona_loader):
    """Verify and possibly correct user story summaries to prioritize persona context over system context."""

    utils = Utils()

    # Load all personas and system summary
    if os.path.exists(utils.USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR):
        print(f"⚠️ User story conflict directory exists: {utils.USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR}. Skipping verification.")
        return

    all_personas = {p.id: p for p in persona_loader.get_personas()}
    system_context = utils.load_system_context()
    user_story_guidelines = utils.load_user_story_guidelines()

    loader = UserStoryLoader()
    loader.load_all_user_stories()
    all_stories = loader.get_all()

    print(f"🔍 Verifying {len(all_stories)} user stories for persona context dominance in summaries...")

    # Load LLM response language proficiency level
    proficiency_level = utils.load_llm_response_language_proficiency_level()

    for story in all_stories:
        persona = all_personas.get(story.persona)
        if not persona:
            print(f"⚠️ Persona {story.persona} not found for story {story.id}. Skipping.")
            continue

        prompt = build_verification_prompt(system_context, user_story_guidelines, persona, story, proficiency_level=proficiency_level)

        try:
            revised_summary = utils.get_llm_response(prompt).strip()
            if revised_summary and revised_summary != story.summary:
                print(f"✏️ Updated summary for story {story.id} (Persona: {story.persona})")
                update_story_summary(story, revised_summary, utils)
            else:
                print(f"✅ Summary for story {story.id} looks good.")
        except Exception as e:
            print(f"❌ LLM error verifying story {story.id}: {e}")

def build_verification_prompt(system_context, guidelines, persona, story, proficiency_level=""):
    """Build prompt instructing LLM to check and correct user story summary."""

    persona_info = persona.to_prompt_string() if hasattr(persona, 'to_prompt_string') else json.dumps(persona.__dict__, indent=2)

    prompt = f"""
You are a Requirement analyst. A requirement made by a persona in a given system may have been misled to make it more logical and smooth with the system, rather than aligning with the persona information, or it may not have been, I can't be sure. Your job is to check the requirement (a.k.a user story) to be 100% sure that the persona information should be dominant in the context of a user story rather than the system context, even if it contradicts some of the content in the system context.

--- SYSTEM CONTEXT ---
{system_context}
------------------------------

--- USER STORY GUIDELINES ---
{guidelines}
------------------------------

--- PERSONA INFORMATION ---
{persona_info}
------------------------------

--- USER STORY ---
Persona's user story for checking:
- ID: {story.id}
- Title: {story.title}
- Summary: {story.summary}
- Pillar: {story.pillar}
- User Group: {story.user_group}
------------------------------

--- TASK ---
Check the above user story summary carefully. If the summary seems more influenced by the system context than the persona, rewrite the summary so that the persona's context and perspective is dominant, even if that means contradicting or modifying the system context aspects. If the summary already properly reflects the persona's perspective, just return it unchanged.
However, please make sure the summary is informative but concise, and avoid unnecessary verbosity. The summary should be a single sentence that captures the essence of the user story from the persona's perspective (please see the USER STORY GUIDELINES above).

Strictly, return ONLY the summary text. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
------------------------------

{proficiency_level}

--- END OF PROMPT ---
"""
    return prompt

def update_story_summary(story, new_summary, utils: Utils = None):
    """Update the summary in the persona's user story JSON file."""
    filename = f"User_stories_for_{story.persona}.json"
    filepath = os.path.join(utils.USER_STORY_DIR, filename)

    if not os.path.exists(filepath):
        print(f"❌ Could not find user story file for persona {story.persona} to update summary.")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        stories = json.load(f)

    updated = False
    for s in stories:
        if s.get("id") == story.id:
            s["summary"] = new_summary
            updated = True
            break

    if updated:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(stories, f, indent=2, ensure_ascii=False)
    else:
        print(f"⚠️ Could not find story {story.id} in persona {story.persona} file to update summary.")
