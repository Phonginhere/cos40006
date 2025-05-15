import os
import re
import json
import textwrap

from pathlib import Path

from pipeline.utils import get_llm_response, load_use_case_task_example, load_system_summary, USE_CASE_TASK_EXTRACTION_DIR
from pipeline.user_persona_loader import UserPersonaLoader
from pipeline.use_case.use_case_loader import UseCaseLoader

def build_task_extraction_prompt(uc, all_personas: dict, system_summary: str) -> str:
    # Extract personas
    involved_personas = [all_personas[pid] for pid in uc.personas if pid in all_personas]
    persona_text = "\n".join(
        f"- {p.id}: {p.name}, {p.role}" for p in involved_personas
    )
    
    # Load example guide text
    example_guide = load_use_case_task_example()

    return textwrap.dedent(f"""
You are a requirements analyst. You are reading a finalized use case from a given system.

Your objective is to extract a **diverse and realistic set of persona tasks**, with a **slight preference for goal-driven functional actions**, while still capturing notable non-functional aspects. Each persona's unique motivations, behaviors, and expectations should be reflected.

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

--- SYSTEM SUMMARY ---

🔍 Below is a short summary of the system:
{system_summary}

--- INVOLVED PERSONAS ---

🧑‍🤝‍🧑 Here are the personas involved in this use case:
{persona_text}

--- USE CASE SCENARIO ---
Here is the scenario for the use case. It describes a specific situation in which the personas interact with the given system. The scenario is a narrative that illustrates how the personas use the system to achieve their goals.

📘 Use Case Overview:
ID: {uc.id}
Name: {uc.name}
Description: {uc.description}
Type: {uc.use_case_type}
Scenario:
{uc.scenario.strip()}


📝 TASK → For each persona listed above:
- Identify all meaningful *tasks* (or operands/actions) they perform in the scenario.
- Include **both action-based** (functional) and **quality-focused** (non-functional) tasks.
- Each task should be written as a short, complete sentence or phrase. Also, they should be distinct, goal-oriented and not repeated across personas.
- Group tasks by persona. In the extracted tasks, please use the persona name, NOT their id, which is only used for the attribute "personaId".

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

--- EXAMPLE ---
{example_guide}

Strictly return only valid JSON. Do not include any extra or invalid texts (e.g. "Task 1" in tasks, or the other information (e.g., name, e.t.c) of persona besides its Id) or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response. Avoid duplications across personas.
""").strip()

def extract_and_save_tasks(uc, all_personas: dict) -> None:
    """Generate persona-level tasks for a use case and save the result."""
    system_summary = load_system_summary()
    prompt = build_task_extraction_prompt(uc, all_personas, system_summary)
    print(f"\n🧠 Extracting persona tasks for {uc.id}...")

    raw = get_llm_response(prompt)
    raw = re.sub(r"```.*?```", "", raw, flags=re.S).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        print(f"❌ Failed to parse JSON for {uc.id}: {raw[:120]}...")
        return
    
    result = {
        "useCaseId": uc.id,
        "tasksByPersona": parsed
    }

    out_path = Path(USE_CASE_TASK_EXTRACTION_DIR) / f"Extracted_tasks_from_{uc.id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"✅ Tasks saved to: {out_path}")
    
def analyze_all_use_cases(persona_loader: UserPersonaLoader) -> None:
    """Run task extraction over all enriched use cases with non-null scenarios."""
    all_personas = {p.id: p for p in persona_loader.get_personas()}

    uc_loader = UseCaseLoader()
    uc_loader.load()
    all_uc = [uc for uc in uc_loader.get_all() if uc.scenario and uc.scenario.strip()]

    # Gather all use case IDs
    expected_uc_ids = {uc.id for uc in all_uc}

    # Gather all filenames in the analysis output folder
    existing_filenames = set(f.name for f in Path(USE_CASE_TASK_EXTRACTION_DIR).glob("*.json"))

    # Extract detected UC-IDs from filenames
    existing_uc_ids = set()
    for filename in existing_filenames:
        for uc_id in expected_uc_ids:
            if uc_id in filename:
                existing_uc_ids.add(uc_id)
                break

    # Compare
    if expected_uc_ids == existing_uc_ids:
        print("✅ All use case task files already exist. Skipping analysis.")
        return

    print("🔁 Mismatch or missing task files. Regenerating all...")
    for f in Path(USE_CASE_TASK_EXTRACTION_DIR).glob("*.json"):
        f.unlink()

    for uc in all_uc:
        extract_and_save_tasks(uc, all_personas)

    print("📦 Task extraction complete.")
