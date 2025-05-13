import os
import re
import json
import textwrap

from pathlib import Path

from utils import get_llm_response, load_use_case_task_example, load_alfred_summary, USE_CASE_TASK_DIR
from user_persona_loader import UserPersonaLoader
from use_cases.use_case_loader import UseCaseLoader

def build_task_extraction_prompt(uc, all_personas: dict, alfred_summary: str) -> str:
    # Extract personas
    involved_personas = [all_personas[pid] for pid in uc.personas if pid in all_personas]
    persona_text = "\n".join(
        f"- {p.id}: {p.name}, {p.role}" for p in involved_personas
    )
    
    # Load example guide text
    example_guide = load_use_case_task_example()

    return textwrap.dedent(f"""
You are a requirements analyst. You are reading a finalized use case from the ALFRED system.

🎯 Your objective is to extract a **diverse and balanced set of persona tasks**, with a **strong emphasis on non-functional concerns**. You must extract tasks that relate to:

- Functional actions (e.g., interactions, operations, commands), and  
- Non-functional expectations, such as:
  • Privacy or security concerns  
  • Usability or accessibility preferences  
  • Trust, safety, or autonomy  
  • Performance expectations or emotional responses  
  • System adaptability, control, or comfort  
  
These tasks will be used to generate user stories that cover both behavioral and quality-of-service aspects of the system. To avoid bias, you must **prioritize non-functional aspects when they appear** in the scenario.
Note that, the term **functional** and **non-functional** should not be used directly in the extracted tasks.

--- ALFRED SYSTEM ---

🔍 Below is a short summary of the ALFRED system:
{alfred_summary}

--- INVOLVED PERSONAS ---

🧑‍🤝‍🧑 Here are the personas involved in this use case:
{persona_text}

--- USE CASE SCENARIO ---
Here is the scenario for the use case. It describes a specific situation in which the personas interact with the ALFRED system. The scenario is a narrative that illustrates how the personas use the system to achieve their goals.

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
- Focus on system-relevant behaviors, motivations, requests, and interactions.

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

Strictly return only valid JSON. Do not include any extra text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response. Avoid duplications across personas.
""").strip()

def extract_and_save_tasks(uc, all_personas: dict) -> None:
    """Generate persona-level tasks for a use case and save the result."""
    alfred_summary = load_alfred_summary()
    prompt = build_task_extraction_prompt(uc, all_personas, alfred_summary)
    print(f"\n🧠 Extracting persona tasks for {uc.id}...")

    raw = get_llm_response(prompt, max_tokens=600)
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

    out_path = Path(USE_CASE_TASK_DIR) / f"Extracted_tasks_from_{uc.id}.json"
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
    existing_filenames = set(f.name for f in Path(USE_CASE_TASK_DIR).glob("*.json"))

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
    for f in Path(USE_CASE_TASK_DIR).glob("*.json"):
        f.unlink()

    for uc in all_uc:
        extract_and_save_tasks(uc, all_personas)

    print("📦 Task extraction complete.")
