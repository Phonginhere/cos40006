import json
import os
import re

from pathlib import Path

from pipeline.user_story.user_story_loader import UserStoryLoader
from pipeline.user_persona_loader import UserPersonaLoader
from pipeline.utils import (
    get_llm_response,
    load_system_summary,
    USE_CASE_TASK_EXTRACTION_DIR,
    USER_STORY_DIR
)

def deduplicate_tasks_for_all_use_cases(persona_loader: UserPersonaLoader):
    system_summary = load_system_summary()
    all_personas = {p.id: p for p in persona_loader.get_personas()}
    
    # Step Skipping Logics – check if all stories are fully generated
    user_story_dir_exists = os.path.exists(USER_STORY_DIR)

    if user_story_dir_exists:
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
            print(f"⏭️ Skipping deduplicating: All user stories for {len(persona_ids)} personas are complete (title, summary, priority, and pillar filled).")
            return
    else:
        print(f"⚠️ Skipping completeness check: Directory '{USER_STORY_DIR}' does not exist.")
        
    task_files = sorted(Path(USE_CASE_TASK_EXTRACTION_DIR).glob("*.json"))

    print(f"🔄 Starting task deduplication across {len(all_personas)} personas...\n")

    for persona_id, persona in all_personas.items():
        print(f"🧠 Processing persona {persona_id}...")

        persona_prompt = persona.to_prompt_string()
        related_files = []

        for fpath in task_files:
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                data = json.loads(fpath.read_text(encoding="latin-1"))

            for entry in data.get("tasksByPersona", []):
                if entry["personaId"] == persona_id:
                    related_files.append((fpath, data))
                    break

        if not related_files:
            print(f"⚠️ No tasks found for persona {persona_id}. Skipping...\n")
            continue

        print(f"📁 Found {len(related_files)} use case files involving {persona_id}.")

        for i in range(len(related_files)):
            base_file, base_data = related_files[i]
            base_tasks = get_persona_tasks(base_data, persona_id)

            for j in range(i + 1, len(related_files)):
                compare_file, compare_data = related_files[j]
                compare_tasks = get_persona_tasks(compare_data, persona_id)

                if not compare_tasks:
                    continue

                print(f"🔍 Comparing UC {base_file.name} ➡️ {compare_file.name} for {persona_id}...")

                dedup_prompt = build_dedup_prompt(
                    system_summary,
                    persona_prompt,
                    base_tasks,
                    compare_tasks
                )

                response = get_llm_response(dedup_prompt)
                new_tasks = parse_json_list(response)

                original_count = len(compare_tasks)
                new_count = len(new_tasks)

                for entry in compare_data["tasksByPersona"]:
                    if entry["personaId"] == persona_id:
                        entry["tasks"] = new_tasks

                compare_file.write_text(
                    json.dumps(compare_data, indent=2, ensure_ascii=False), encoding="utf-8"
                )

                removed = original_count - new_count
                print(f"✅ Updated {compare_file.name}: {removed} redundant task(s) removed.")

        print(f"✔️ Finished deduplicating tasks for {persona_id}.\n")

    print("✅ Task deduplication complete for all personas.\n")


def get_persona_tasks(use_case_data: dict, persona_id: str):
    for entry in use_case_data.get("tasksByPersona", []):
        if entry["personaId"] == persona_id:
            return entry.get("tasks", [])
    return []


def build_dedup_prompt(system_summary: str, persona_prompt: str, existing_tasks: list, new_tasks: list):
    return f"""You are helping with system requirement engineering for a project as follows:

SYSTEM SUMMARY:
{system_summary}

PERSONA DETAILS:
{persona_prompt}

Below is a list of tasks previously extracted from other use cases for this persona:
List A (existing tasks):
{json.dumps(existing_tasks, indent=2)}

Now, here is another list of tasks from a new use case:
List B (new tasks):
{json.dumps(new_tasks, indent=2)}

Your job is to refine List B. Please remove any task that is already covered or **extremely similar** in content or meaning to a task in List A — taking into account the **system context** and **persona information** mentioned above.

⚠️ Only remove tasks that are clearly overlapping. Do NOT remove tasks unless they are redundant or nearly identical.

[
  "Unique Task 1",
  "Unique Task 2",
  ...
]

Return ONLY the updated List B as a valid JSON list of strings. Do not include any extra or invalid texts (e.g. "Task 1", "Unique Task 2", or any other redundant information (e.g., name, e.t.c) of persona besides its Id) or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response. Avoid duplications across personas.
""".strip()


def parse_json_list(text: str):
    """Extract JSON list from raw LLM response."""
    try:
        match = re.search(r"\[\s*[\s\S]*?\s*\]", text)
        if match:
            json_text = match.group(0)
            json_text = json_text.replace("“", "\"").replace("”", "\"").replace("’", "'")
            return json.loads(json_text)
    except json.JSONDecodeError:
        pass
    print("⚠️ Could not parse tasks from LLM response. Returning original.")
    return []