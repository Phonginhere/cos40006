import os
import json
from pathlib import Path

from pipeline.user_persona_loader import UserPersonaLoader
from pipeline.utils import (
    get_llm_response,
    load_system_summary,
    USER_STORY_DIR,
)


def build_batch_dedup_prompt(system_summary: str, user_stories: list) -> str:
    examples = [
        {"id": story["id"], "summary": story["summary"]}
        for story in user_stories if story["summary"]
    ]

    return f"""You are a requirements engineer. You are helping with system requirement engineering for a project as follows:

SYSTEM SUMMARY:
{system_summary}

Below is a list of user stories written by the same persona. Each user story is represented by an ID and its summary.

Your job is to identify which user stories are redundant, overly similar, or express the same intent in slightly different ways. These may include reworded duplicates, near duplicates, or stories with the same goal phrased differently.

ONLY return the list of IDs of user stories that should be removed because they are duplicates or redundant. Return this as a valid JSON array of IDs.

USER STORIES:
{json.dumps(examples, indent=2)}

📌 OUTPUT FORMAT - JSON array of IDs to remove (Below is just an example)):
[
  "US-017",
  "US-021",
  ...
]

Return ONLY the list likes the above example. Do not include any explanation, commentary, or formatting. Do NOT use any markdown, bold, italic, or special formatting in your response.
""".strip()


def deduplicate_user_stories_for_each_persona(persona_loader: UserPersonaLoader):
    system_summary = load_system_summary()
    all_personas = {p.id: p for p in persona_loader.get_personas()}
    story_dir = Path(USER_STORY_DIR)
    story_files = sorted(story_dir.glob("User_stories_for_*.json"))

    print(f"🔍 Starting batch deduplication for {len(story_files)} personas...\n")

    for file_path in story_files:
        persona_id = file_path.stem.split("_for_")[-1]
        if persona_id not in all_personas:
            print(f"⚠️ Persona {persona_id} not found. Skipping.")
            continue

        try:
            stories = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"❌ Failed to read {file_path.name}: {e}")
            continue

        if len(stories) <= 1:
            continue

        print(f"🧠 Deduplicating {len(stories)} user stories for {persona_id}...")

        prompt = build_batch_dedup_prompt(system_summary, stories)
        response = get_llm_response(prompt)

        try:
            to_remove_ids = json.loads(response)
            if not isinstance(to_remove_ids, list):
                raise ValueError("Expected a list of IDs.")
        except Exception as e:
            print(f"⚠️ LLM response parsing failed for {persona_id}: {e}")
            continue

        deduplicated = [s for s in stories if s["id"] not in to_remove_ids]
        removed = len(stories) - len(deduplicated)

        file_path.write_text(json.dumps(deduplicated, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ Removed {removed} duplicates → {file_path.name}\n")

    print("🎉 Batch user story deduplication complete.\n")
