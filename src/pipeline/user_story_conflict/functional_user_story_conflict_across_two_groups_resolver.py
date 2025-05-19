import os
import json
from typing import Optional

from pipeline.utils import (
    UserPersonaLoader,
    Utils,
)


def load_json_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_resolution_prompt(
    system_context: str,
    user_story_guidelines: str,
    technique_summary: str,
    personaA,
    personaB,
    storyA_summary: str,
    storyB_summary: str,
    conflictType: str,
    conflictDescription: str,
    proficiency_level: str = "",
) -> str:
    prompt = f"""
You are an expert system requirements engineer. You are resolving functional user story conflicts across two different user groups. You will analyze the conflict between two functional user stories and provide a resolution strategy.

--- SYSTEM CONTEXT ---
{system_context}
-------------------------------------

--- RESOLUTION TECHNIQUE ---
Apply the Chentouf technique for resolving functional user story conflicts (across two different user groups):
{technique_summary}

--- CONFLICT ---
Conflict Type: {conflictType}
Conflict Description: {conflictDescription}

User Story A Summary:
{storyA_summary}

User Story B Summary:
{storyB_summary}
-------------------------------------

--- YOUR TASK ---
The summary **may* or **may not** be adjusted so the conflict is no longer valid. Carefully analyze if the conflict described is still present given the current summaries.

- If the conflict is NO LONGER valid, respond with ONLY:
None

- If the conflict is still valid, analyze the conflict based on the given Chentouf's technique and choose ONE of the following four resolution types (return exactly the type text, no quotes):
  1. Update both user stories
  2. Update one and keep one remain the same
  3. Update one and discard the other
  4. Keep one remain and discard the other

Then provide a concise resolution description explaining how the resolution strategy is applied.

Finally, provide the NEW summaries for both user stories according to the resolution:
- If a user story is discarded, its summary should be an empty string.
- If updated or kept, provide the updated or original summary respectively. If updated, **unlike the original user story summary (summaries)**, which is mostly dominant by the persona's information; your **updated summary (summaries)** must be smooth, consistent, and coherent, respecting the system summary. That means, at least one of the personas' information should partially be sacrificed for the coherence, consistence and smoothness.
(Note that, a user story's summary is a short and precise user story in 1-2 sentences. Generally, it is limited to about 10 to 25 words. General format is: As a/an + [<role, or type of user>, 2-3 words], I would like to/want to/do not want to/... + [<some goal>, 4-6 words], so that + [<some reason>, 5-7 words])
Respond STRICTLY in the JSON format:

{{
    "generalResolutionType": "(strictly, one of the four exact types above (do not include quotes, just the text))",
    "resolutionDescription": "(A short description of how the resolution strategy is applied)",
    "newUserStoryASummary": "(updated or original summary A or empty string if discarded)",
    "newUserStoryBSummary": "(updated or original summary B or empty string if discarded)"
}}

Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
-------------------------------------

{proficiency_level}

--- END OF PROMPT ---
"""
    return prompt.strip()


def parse_llm_response(raw: str) -> Optional[dict]:
    try:
        import re
        raw_clean = re.sub(r"```(json)?", "", raw).strip()
        data = json.loads(raw_clean)

        required_keys = {
            "generalResolutionType",
            "resolutionDescription",
            "newUserStoryASummary",
            "newUserStoryBSummary",
        }
        if not all(k in data for k in required_keys):
            return None

        # Treat "None" or empty resolution type as no resolution
        if not data["generalResolutionType"] or data["generalResolutionType"].strip().lower() == "none":
            return None

        return data
    except Exception as e:
        print(f"❌ Failed to parse LLM response: {e}")
        print(f"Response snippet: {raw[:300]}")
        return None


def update_user_story_file_by_persona(persona_id: str, story_id: str, new_summary: str, utils: Utils):

    filepath = os.path.join(utils.USER_STORY_DIR, f"User_stories_for_{persona_id}.json")
    if not os.path.exists(filepath):
        print(f"⚠️ User story file for persona {persona_id} not found: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        stories = json.load(f)

    idx = next((i for i, s in enumerate(stories) if s.get("id") == story_id), None)
    if idx is None:
        print(f"⚠️ Story {story_id} not found in persona {persona_id} file")
        return

    if not new_summary.strip():
        print(f"🗑️ Removing story {story_id} from persona {persona_id} file due to empty summary")
        stories.pop(idx)
    else:
        stories[idx]["summary"] = new_summary

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(stories, f, indent=2, ensure_ascii=False)


def resolve_functional_conflicts_across_two_groups(persona_loader: UserPersonaLoader):
    utils = Utils()
    
    system_context = utils.load_system_context()
    user_story_guidelines = utils.load_user_story_guidelines()
    technique_summary = utils.load_functional_user_story_conflict_technique_description()

    all_personas = {p.id: p for p in persona_loader.get_personas()}
    
    # Load LLM response language proficiency level
    proficiency_level = utils.load_llm_response_language_proficiency_level()

    # Load all user stories from USER_STORY_DIR by reading all persona files and indexing by story ID
    user_stories = {}
    for fname in os.listdir(utils.USER_STORY_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            path = os.path.join(utils.USER_STORY_DIR, fname)
            stories = load_json_file(path)
            for story in stories:
                user_stories[story["id"]] = story
        except Exception as e:
            print(f"⚠️ Failed to load user stories from {fname}: {e}")

    conflict_files = [
        f for f in os.listdir(utils.FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR)
        if f.endswith(".json")
    ]

    for conflict_file in conflict_files:
        conflict_path = os.path.join(utils.FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR, conflict_file)
        try:
            conflicts = load_json_file(conflict_path)
        except Exception as e:
            print(f"❌ Failed to load conflicts file {conflict_file}: {e}")
            continue

        # Skip if all conflicts already resolved (have resolution fields)
        if all("generalResolutionType" in c and "resolutionDescription" in c for c in conflicts):
            print(f"⏭️ Skipping {conflict_file} - all conflicts already have resolution.")
            continue

        updated = False

        for conflict in conflicts:
            if "generalResolutionType" in conflict and conflict["generalResolutionType"]:
                continue

            a_id = conflict.get("userStoryAId")
            b_id = conflict.get("userStoryBId")

            # Check both stories exist in user stories loaded
            if a_id not in user_stories or b_id not in user_stories:
                print(f"⚠️ Skipping conflict {conflict.get('conflictId')} because user story missing.")
                continue

            storyA_data = user_stories[a_id]
            storyB_data = user_stories[b_id]

            personaA = all_personas.get(conflict.get("personaAId"))
            personaB = all_personas.get(conflict.get("personaBId"))

            if not personaA or not personaB:
                print(f"⚠️ Skipping conflict {conflict.get('conflictId')} because persona missing.")
                continue

            prompt = build_resolution_prompt(
                system_context,
                user_story_guidelines,
                technique_summary,
                personaA,
                personaB,
                storyA_data.get("summary", ""),
                storyB_data.get("summary", ""),
                conflict.get("conflictType", ""),
                conflict.get("conflictDescription", ""),
                proficiency_level,
            )

            response = utils.get_llm_response(prompt)
            if not response:
                print(f"⚠️ Empty LLM response for conflict {conflict.get('conflictId')}")
                continue

            parsed = parse_llm_response(response)
            if not parsed:
                print(f"⚠️ Invalid or None resolution for conflict {conflict.get('conflictId')}")
                conflict.update({
                    "generalResolutionType": "",
                    "resolutionDescription": "",
                    "newUserStoryASummary": "",
                    "newUserStoryBSummary": "",
                })
                updated = True
                continue

            conflict.update({
                "generalResolutionType": parsed["generalResolutionType"],
                "resolutionDescription": parsed["resolutionDescription"],
                "newUserStoryASummary": parsed["newUserStoryASummary"],
                "newUserStoryBSummary": parsed["newUserStoryBSummary"],
            })
            updated = True

            # Update user story files accordingly (per persona)
            update_user_story_file_by_persona(conflict.get("personaAId"), a_id, parsed["newUserStoryASummary"], utils)
            update_user_story_file_by_persona(conflict.get("personaBId"), b_id, parsed["newUserStoryBSummary"], utils)

        if updated:
            try:
                save_json_file(conflict_path, conflicts)
                print(f"✅ Updated conflict file saved: {conflict_file}")
            except Exception as e:
                print(f"❌ Failed to save updated conflict file {conflict_file}: {e}")
