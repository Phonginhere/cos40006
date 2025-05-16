import os
import json
import re
from typing import Optional

from pipeline.user_story.user_story_loader import UserStoryLoader, UserStory
from pipeline.utils import (
    CURRENT_LLM,
    USER_GROUP_KEYS,
    NON_FUNCTIONAL_USER_STORY_DECOMPOSITION_PATH,
    load_system_summary,
    load_user_group_guidelines,
    load_user_story_guidelines,
    load_non_functional_user_story_conflict_summary,
    get_llm_response,
)


def decompose_non_functional_user_stories(user_story_loader: Optional[UserStoryLoader] = None):
    # Load or create output directory and loader
    loader = user_story_loader if user_story_loader else UserStoryLoader()
    loader.load_all_user_stories()
    nf_stories = loader.filter_by_type("Non-Functional")

    # Skip if analysis already exists with all entries
    if os.path.exists(NON_FUNCTIONAL_USER_STORY_DECOMPOSITION_PATH):
        with open(NON_FUNCTIONAL_USER_STORY_DECOMPOSITION_PATH, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            if isinstance(existing_data, list) and len(existing_data) == len(nf_stories):
                print("✅ Skipping NFUS decomposition — already analyzed.")
                return

    print(f"🔍 Decomposing {len(nf_stories)} non-functional user stories...")

    system_summary = load_system_summary()
    story_summary = load_user_story_guidelines()
    technique_summary = load_non_functional_user_story_conflict_summary()

    all_results = []

    for story in nf_stories:
        group_key = USER_GROUP_KEYS.get(story.user_group)
        if not group_key:
            continue

        user_group_summary = load_user_group_guidelines(group_key)

        prompt = build_decomposition_prompt(
            technique_summary,
            system_summary,
            user_group_summary,
            story_summary,
            story
        )
        response = get_llm_response(prompt)

        # Fallback handling: if response is None or parsing fails, use story.summary as single decomposition element
        if response is None:
            print(f"⚠️ LLM response is None for story {story.id}, using fallback decomposition.")
            decomposition = [story.summary]
        else:
            decomposition = parse_decomposition_response(response)
            if decomposition is None:
                print(f"⚠️ Failed to parse LLM response for story {story.id}, using fallback decomposition.")
                decomposition = [story.summary]

        all_results.append({
            **story.to_dict(),
            "decomposition": decomposition
        })

        # print(f"✅ Decomposed NFUS (ID: {story.id}, Persona: {story.persona}, decomposition: {decomposition})")

    with open(NON_FUNCTIONAL_USER_STORY_DECOMPOSITION_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved decompositions to: {NON_FUNCTIONAL_USER_STORY_DECOMPOSITION_PATH}")


def build_decomposition_prompt(technique_summary: str, system_summary: str,
                                user_group_summary: str, story_summary: str,
                                story: UserStory) -> str:
    return f"""
You are an expert in non-functional requirement analysis. Apply the Sadana and Liu technique described below to decompose a non-functional user story into its lowest-level non-functional requirements:

{technique_summary}

====================
System Context:
====================
{system_summary}

====================
User Group Summary:
====================
{user_group_summary}

====================
User Story Guidelines:
====================
{story_summary}

====================
Decompose the following non-functional user story.

User Story (ID: {story.id}, Persona: {story.persona}):
Title: {story.title}
Summary: {story.summary}

====================
Decomposition Instructions:

• Your output must be a small list (1-3, depends on the complicated level of the given user story's summary) of atomic non-functional requirements (NFRs) that represent this user story.
• Only include more than 3 if **absolutely necessary** — avoid over-decomposition.
• Each NFR should be:
  – Short, concrete, and **standalone**.
  – Non-overlapping and non-repetitive.
  – Strictly derived from the user story's actual intent — avoid generic expansions or technical over-specification.
• Do NOT split every adjective or clause into separate NFRs unless they clearly indicate different goals.
• If the original story is simple, keep the decomposition small and focused.

====================
Your response must be a JSON object in the format:
{{
  "decomposition": [
    "(lowest-level NFR 1)",
    "(lowest-level NFR 2)",
    ...
  ]
}}

Strictly, do not include any additional text or commentary (e.g., "A1", "B2", "NFR3", e.t.c in decomposition's elements). Do NOT use any markdown, bold, italic, or special formatting in your response.
""".strip()


def parse_decomposition_response(raw: str) -> Optional[list]:
    try:
        raw = re.sub(r"```(json)?", "", raw).strip()
        parsed = json.loads(raw)
        return parsed.get("decomposition")
    except Exception as e:
        print(f"❌ Failed to parse decomposition: {e}")
        print(f"Raw response:\n{raw[:300]}")
        return None
