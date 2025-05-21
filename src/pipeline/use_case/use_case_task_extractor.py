import os
import re
import json
import textwrap

from pathlib import Path
from collections import defaultdict

from pipeline.utils import (
    UserPersonaLoader,
    Utils,
)
from pipeline.use_case.use_case_loader import UseCaseLoader


def build_task_extraction_prompt(
    uc, 
    all_personas: dict, 
    system_context: str,
    proficiency_level: str = "",
    example_guide: str = "",
) -> str:
    utils = Utils()
    
    involved_personas = [all_personas[pid] for pid in uc.personas if pid in all_personas]
    persona_text = "\n".join(
        f"- {p.id}: {p.name}, {p.role}" for p in involved_personas
    )

    return textwrap.dedent(f"""
You are a requirements analyst. You are reading a finalized use case from a given system.

--- SYSTEM CONTEXT ---
🔍 Below is a short summary of the system:
{system_context}
-------------------------------------

--- INVOLVED PERSONAS ---
🧑‍🤝‍🧑 Here are the personas involved in this use case:
{persona_text}
-------------------------------------

--- USE CASE SCENARIO ---
Here is the scenario for the use case. It describes a specific situation in which the personas interact with the given system. The scenario is a narrative that illustrates how the personas use the system to achieve their goals.

📘 Use Case Overview:
ID: {uc.id}
Name: {uc.name}
Description: {uc.description}
Type: {uc.use_case_type}
Scenario:
{uc.scenario.strip()}
-------------------------------------

--- YOUR TASK ---
Your objective is to extract a **diverse and realistic set of persona tasks**, with a **slight preference for goal-driven functional actions**, while still capturing notable non-functional aspects...

You must extract tasks that relate to:
- **Functional tasks** – goal-directed **actions, operations, or interactions** that personas perform with or around the system.
- **Non-functional tasks** – **expectations, emotional reactions, usability constraints, or autonomy/trust-related behaviors** if explicitly expressed.
  
📌 PRIORITIZATION:
- Prioritize **explicit user interactions** (e.g., commands, configuration, inputs, navigation, adjustments, toggling options) as concrete functional tasks.
- Follow with complementary **experience-based or constraint-based** expectations (non-functional).
- Target a **functional to non-functional** split ranging from 60–40 to 70–30**, depending on the use case and the richness of action-context available.
  
📌 IMPORTANT:
- Focus on **persona-specific interpretations and desires** over what the use case *description* or *system context* implies.
- If a persona appears overly controlling, passive, anxious, skeptical, curious, or even dismissive — let that show in the tasks.
- It is acceptable (and encouraged) for tasks to reflect **contrasting or conflicting goals** between personas.
- Do **not** smooth over differences or rationalize tasks for consistency.
- Avoid copying generic use case logic — only extract what is evident from how the persona *personally engages* with the system.
- Extract **both types** of tasks, with slightly more weight on concrete **actions or interactions** (functional). However, the terms **functional** and **non-functional** should hardly be used directly in the extracted tasks.

To summarize, for each persona listed above:
- Identify all meaningful *tasks* (or operands/actions) they perform in the scenario.
- Include **both action-based** (functional) and **quality-focused** (non-functional) tasks.
- Each task should be written as a short, complete sentence or phrase. Also, they should be distinct, goal-oriented and not repeated across personas.
- Group tasks by persona. In the extracted tasks, please use the persona name, NOT their id, which is only used for the attribute "personaId".
- Strictly, please note that each task from a persona should not only from the use case only, but must align with that involved persona's information. In **most** cases, especially where the use case's relevant section(s) are quite general, abstract and/or vague, the persona's information should be the **dominant factor** in the task extraction and/or generation process(es).
- Also, the tasks must be unique. So please skip any similar operands, actions, e.t.c.
-----------------------------------------

--- OUTPUT FORMAT ---

Output a **JSON array** with the following structure:
[
  {{
    "personaId": "P-XXX",
    "tasks": [
      "Task 1...",
      "Task 2...",
      ...
    ]
  }},
  ...
]

For example:
{example_guide}

Strictly return only valid JSON. Do not include any extra or invalid texts (e.g. "Task 1" in tasks, or the other information (e.g., name, e.t.c) of persona besides its Id) or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response. Avoid duplications across personas.
-----------------------------------------

{proficiency_level}

--- END OF PROMPT ---
""").strip()


def extract_and_save_tasks(uc, all_personas: dict) -> dict:
    """Generate persona-level tasks for a use case and return as dict."""
    utils = Utils()

    # Load system context and proficiency level
    system_context = utils.load_system_context()
    proficiency_level = utils.load_llm_response_language_proficiency_level()

    # Load example guide
    example_guide = utils.load_use_case_task_example()

    prompt = build_task_extraction_prompt(uc, all_personas, system_context, proficiency_level, example_guide)
    print(f"\n🧠 Extracting persona tasks for {uc.id}...")

    raw = utils.get_llm_response(prompt)
    raw = re.sub(r"```.*?```", "", raw, flags=re.S).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        print(f"❌ Failed to parse JSON for {uc.id}: {raw[:120]}...")
        return None

    return {
        "useCaseId": uc.id,
        "tasksByPersona": parsed
    }


def reformat_and_save_all_tasks_by_persona():
    utils = Utils()

    task_dir = Path(utils.EXTRACTED_USE_CASE_TASKS_DIR)
    files = sorted(task_dir.glob("Extracted_tasks_from_UC-*.json"))
    flat_task_list = []
    task_counter = 1

    for file in files:
        with file.open("r", encoding="utf-8") as f:
            data = json.load(f)
            uc_id = data.get("useCaseId", "")
            for persona_entry in data.get("tasksByPersona", []):
                persona_id = persona_entry.get("personaId", "")
                for desc in persona_entry.get("tasks", []):
                    flat_task_list.append({
                        "taskID": f"TASK-{task_counter:03}",
                        "useCaseId": uc_id,
                        "personaId": persona_id,
                        "taskDescription": desc
                    })
                    task_counter += 1

    # Group by personaId
    grouped = defaultdict(list)
    for task in flat_task_list:
        grouped[task["personaId"]].append(task)

    # Write to separate JSON files
    for persona_id, tasks in grouped.items():
        out_path = task_dir / f"Extracted_tasks_for_{persona_id}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(tasks)} tasks for {persona_id} → {out_path.name}")


def extract_tasks_from_all_use_cases(persona_loader: UserPersonaLoader):
    all_personas = {p.id: p for p in persona_loader.get_personas()}
    uc_loader = UseCaseLoader()
    uc_loader.load()
    all_uc = [uc for uc in uc_loader.get_all() if uc.scenario and uc.scenario.strip()]

    utils = Utils()

    os.makedirs(utils.EXTRACTED_USE_CASE_TASKS_DIR, exist_ok=True)

    # Check if we can skip the extraction
    persona_files = set(f for f in os.listdir(utils.EXTRACTED_USE_CASE_TASKS_DIR) if f.startswith("Extracted_tasks_for_") and f.endswith(".json"))
    expected_files = {f"Extracted_tasks_for_{pid}.json" for pid in all_personas.keys()}
    
    if expected_files.issubset(persona_files) and len(expected_files) == len(all_personas):
        print("⏭️ Skipping task extraction — all tasks already extracted.")
        return

    for uc in all_uc:
        file_path = os.path.join(utils.EXTRACTED_USE_CASE_TASKS_DIR, f"Extracted_tasks_from_{uc.id}.json")
        if os.path.exists(file_path):
            print(f"⏭️ Skipping {uc.id} – already extracted.")
            continue

        extracted = extract_and_save_tasks(uc, all_personas)
        if extracted:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(extracted, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved → {file_path}")

    reformat_and_save_all_tasks_by_persona()