import os
import json
import re
from pathlib import Path

from pipeline.user_persona_loader import UserPersonaLoader
from pipeline.user_story.user_story_loader import UserStoryLoader
from pipeline.utils import (
    get_llm_response,
    load_system_summary,
    USE_CASE_TASK_EXTRACTION_DIR,
    USER_STORY_DIR,
    DUPLICATE_REMOVAL_RATIO_LIMIT
)


def build_pairwise_dedup_prompt(system_summary: str, persona_prompt: str, task_a: str, task_b: str) -> str:
    return f"""You are helping with system requirement engineering for a project as follows:

SYSTEM SUMMARY:
{system_summary}

PERSONA DETAILS:
{persona_prompt}

You are comparing two tasks that were extracted independently for the same persona. Determine if they mean the same thing or are so similar that one can be removed.

TASK A:
"{task_a}"

TASK B:
"{task_b}"

Do these tasks clearly mean the same thing or overlap to the extent that one should be removed? Reply strictly with:
- "Yes" if they are redundant, or similar to each other.
- "No" if both should be kept.

Only respond with "Yes" or "No". Do not include any other text, commentary or explanation. Do NOT use any markdown, bold, italic, or special formatting in your response.
""".strip()


def deduplicate_tasks_for_all_use_cases(persona_loader: UserPersonaLoader):
    system_summary = load_system_summary()
    all_personas = {p.id: p for p in persona_loader.get_personas()}

    # Step Skipping Logics – check if all stories are fully generated
    user_story_dir_exists = os.path.exists(USER_STORY_DIR)

    if user_story_dir_exists:
        loader = UserStoryLoader()
        loader.load_all_user_stories()
        all_stories = loader.get_all()

        persona_ids = set(p.id for p in all_personas.values())
        complete_personas = {
            pid for pid in persona_ids
            if all(
                story.title and story.summary and story.priority is not None and story.pillar
                for story in loader.get_by_persona(pid)
            )
        }

        if complete_personas == persona_ids:
            print(f"⏭️ Skipping deduplicating: All user stories for {len(persona_ids)} personas are complete (title, summary, priority, and pillar filled).")
            return
    else:
        print(f"⚠️ Skipping completeness check: Directory '{USER_STORY_DIR}' does not exist.")

    task_dir = Path(USE_CASE_TASK_EXTRACTION_DIR)
    uc_based_files = list(task_dir.glob("Extracted_tasks_from_UC-*.json"))

    # Step Skipping Logic – all UC-based files already removed
    if not uc_based_files:
        print(f"⏭️ Skipping deduplication: All UC-based task files already removed from '{USE_CASE_TASK_EXTRACTION_DIR}'.")
        return
    
    persona_files = sorted(task_dir.glob("Extracted_tasks_for_*.json"))

    print(f"🔍 Starting fine-grained task deduplication for {len(persona_files)} personas...\n")

    for file_path in persona_files:
        persona_id = file_path.stem.split("_for_")[-1]
        persona = all_personas.get(persona_id)
        if not persona:
            print(f"⚠️ Persona {persona_id} not found in loader. Skipping.")
            continue

        try:
            tasks = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"❌ Failed to read tasks for {persona_id}: {e}")
            continue

        total_tasks = len(tasks)
        if total_tasks == 0:
            continue

        print(f"🧠 Deduplicating {total_tasks} tasks for {persona_id}...")

        persona_prompt = persona.to_prompt_string()
        deduplicated = []
        removed_count = 0
        max_removable = int(total_tasks * DUPLICATE_REMOVAL_RATIO_LIMIT)

        for i, task in enumerate(tasks):
            duplicate = False
            for prior in deduplicated:
                prompt = build_pairwise_dedup_prompt(
                    system_summary,
                    persona_prompt,
                    prior["taskDescription"],
                    task["taskDescription"]
                )
                response = get_llm_response(prompt).strip().lower()
                if response == "yes":
                    removed_count += 1
                    duplicate = True
                    print(f"🗑️ Duplicate found: \"{task['taskDescription']}\" ≈ \"{prior['taskDescription']}\"")
                    break

            if removed_count >= max_removable:
                print(f"⚠️ Stopping early for {persona_id} — {removed_count} duplicates reached threshold ({max_removable}).")
                deduplicated.extend(tasks[i:])  # Keep remaining tasks unfiltered
                break

            if not duplicate:
                deduplicated.append(task)

        # Save the deduplicated version
        file_path.write_text(json.dumps(deduplicated, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ {removed_count} duplicates removed → {file_path.name}\n")

    # Clean up original use-case based files
    for file in task_dir.glob("Extracted_tasks_from_UC-*.json"):
        try:
            file.unlink()
            print(f"🧹 Removed file: {file.name}")
        except Exception as e:
            print(f"⚠️ Could not remove {file.name}: {e}")

    print("🎉 Deduplication complete for all personas.\n")