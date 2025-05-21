import os
import re
import json
import textwrap

from typing import List

from pipeline.use_case.use_case_loader import UseCaseLoader
from pipeline.utils import (
    UserPersonaLoader,
    Utils
)

# ========== Step b: Prompt Constructor ==========
def build_raw_use_case_prompt(
    uc,
    all_personas: dict,
    system_context: str,
    uc_guidelines: str,
    user_groups_guidelines: dict,
    prev_names: List[str],
) -> str:

    persona_blocks, group_set = [], set()

    for pid in uc.personas:
        if persona := all_personas.get(pid):
            persona_blocks.append(f"---\n{persona.to_prompt_string()}")
            group_set.add(persona.user_group)

    persona_text = "\n".join(persona_blocks)
    group_ctx = "\n\n".join(f"{g}:\n{user_groups_guidelines[g]}" for g in sorted(group_set))
    prev_names_block = "\n".join(f"- {n}" for n in prev_names) or "None"

    return textwrap.dedent(
        f"""
You are a system requirements engineer. You are generating a suitable name and a description for a use case of a given system, with "name" is LIKELY a specific subtype of the give useCaseType, otherwise it must be related to the useCaseType.

Firstly, below is the summary of the system:

--- SYSTEM CONTEXT ---
{system_context}

--- USER GROUP CONTEXT ---
Here are summaries of user groups involved in this use case:
{group_ctx}

--- USE-CASE DEFINITION & NOT-REAL EXAMPLES  ---
{uc_guidelines}
-----------------------------

--- YOUR TASK ---
Now consider the following in-progress use case (skeleton):

Use Case ID: {uc.id}
Use Case Type: {uc.use_case_type}
Use Case Pillar(s): {', '.join(uc.pillars)}
Associated User Groups: {', '.join(uc.user_groups)}
Involved Personas:
{persona_text}

Your task is to generate the following missing fields for this use case:
- "name": A concise, clear use case `"name"` (<= 6 words, Title-Case). The name must be **unique**, avoid duplicating any of the previous names, which include: {prev_names_block}
The name should align logically with above information, especially the use case type (Prefer a *more specific sub-type* of the given `use_case_type`; if that’s impossible, ensure the name is obviously related to the type).
- "description": 1–3 sentences explaining the purpose and context of the use case clearly.

Return a single valid JSON object like:
{{
  "name": "...",
  "description": "..."
}}

Strictly return only the JSON object. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
--------------------------------------

--- END OF PROMPT ---
""").strip()


# ========== Step b: Main Entry - Generate Raw Use Cases ==========
def generate_raw_use_cases(persona_loader: UserPersonaLoader) -> None:
    utils = Utils()
    
    os.makedirs(utils.USE_CASE_DIR, exist_ok=True)

    system_context = utils.load_system_context()
    uc_guidelines = utils.load_use_case_guidelines()
    user_groups_guidelines = utils.load_all_user_group_descriptions()

    all_personas = {p.id: p for p in persona_loader.get_personas()}
    uc_loader = UseCaseLoader()
    uc_loader.load()
    
    # Check if all use cases are skeletons (no name, description, scenario)
    if all(not uc.name and not uc.description and not uc.scenario for uc in uc_loader.get_all()):
        print("\n🧠 Detected all use cases are skeletons. Proceeding with raw use case generation...")
    else:
        print("\n✅ Use cases already contain names/descriptions. Skipping raw generation.")
        return

    existing_names: List[str] = [
        uc.name.strip() for uc in uc_loader.get_all() if uc.name.strip()
    ]

    for uc in uc_loader.get_all():
        need_name = not uc.name
        need_desc = not uc.description
        if not (need_name or need_desc):
            print(f"⏭️  {uc.id} already complete.")
            continue
        if not uc.personas:
            print(f"⚠️  {uc.id} has no personas; skipped.")
            continue

        prompt = build_raw_use_case_prompt(
            uc, all_personas, system_context, uc_guidelines, user_groups_guidelines, existing_names
        )

        print(f"\n🧠  Asking model for {uc.id} ...")
        raw = utils.get_llm_response(prompt)

        raw = re.sub(r"```.*?```", "", raw, flags=re.S)

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            print(f"❌  Bad JSON for {uc.id}: {raw[:120]} ...")
            continue

        if need_name:
            uc.name = result.get("name", "").strip()
            if uc.name.lower() in (n.lower() for n in existing_names):
                uc.name += " (Alt)"
            existing_names.append(uc.name)
        if need_desc:
            uc.description = result.get("description", "").strip()

        print(f"✅  {uc.id} → “{uc.name}”")  # success

    uc_loader.save_all()
    print("💾  Raw-name/description generation complete.")
