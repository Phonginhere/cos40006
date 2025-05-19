import os
import json
from pathlib import Path

from pipeline.utils import (
    UserPersonaLoader,
    Utils,
)


def build_batch_dedup_prompt(system_context: str, tasks: list, persona_prompt: str) -> str:
    examples = [
        {"taskID": task["taskID"], "description": task["taskDescription"]}
        for task in tasks if task.get("taskDescription")
    ]

    return f"""You are a requirements engineer. You are helping with system requirement engineering for a project as follows:

--- SYSTEM CONTEXT ---
{system_context}
---------------------------------------

--- PERSONA CONTEXT ---
{persona_prompt}
---------------------------------------

--- TASKS LIST ---
Below is a list of persona tasks extracted from use case scenarios for the same persona. Each task has a task ID and a task description.
Your job is to identify which tasks are redundant, overly similar, or express the same functional or non-functional expectation in slightly different ways. These may include tasks that share the same goal, phrasing, or execution context.

Return ONLY the list of task IDs that should be removed because they are duplicates or redundant. Format your response as a **valid JSON array of task IDs**.

{json.dumps(examples, indent=2)}
---------------------------------------

--- OUTPUT FORMAT – JSON list ---
The output is a list of task IDs to remove (e.g.):
[
  "TASK-022",
  "TASK-034",
  ...
]

Return ONLY the list likes the above example. Do not include any explanation, commentary, or formatting. Do NOT use any markdown, bold, italic, or special formatting in your response.
----------------------------------------

--- END OF PROMPT ---
""".strip()


def deduplicate_tasks_for_all_use_cases(persona_loader: UserPersonaLoader):
    utils = Utils()

    system_context = utils.load_system_context()
    all_personas = {p.id: p for p in persona_loader.get_personas()}
    task_dir = Path(utils.USE_CASE_TASK_EXTRACTION_DIR)
    persona_files = sorted(task_dir.glob("Extracted_tasks_for_*.json"))

    print(f"🔍 Starting batch task deduplication for {len(persona_files)} personas...\n")

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

        if len(tasks) <= 1:
            continue

        print(f"🧠 Deduplicating {len(tasks)} tasks for {persona_id}...")

        prompt = build_batch_dedup_prompt(system_context, tasks, persona.to_prompt_string())
        response = utils.get_llm_response(prompt)

        try:
            to_remove_ids = json.loads(response)
            if not isinstance(to_remove_ids, list):
                raise ValueError("Expected a list of task IDs.")
        except Exception as e:
            print(f"⚠️ LLM response parsing failed for {persona_id}: {e}")
            continue

        deduplicated = [t for t in tasks if t["taskID"] not in to_remove_ids]
        removed = len(tasks) - len(deduplicated)

        file_path.write_text(json.dumps(deduplicated, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ Removed {removed} duplicate tasks → {file_path.name}\n")

    # Clean up original UC-based task files
    for file in task_dir.glob("Extracted_tasks_from_UC-*.json"):
        try:
            file.unlink()
            print(f"🧹 Removed file: {file.name}")
        except Exception as e:
            print(f"⚠️ Could not remove {file.name}: {e}")

    print("🎉 Task deduplication complete for all personas.\n")
