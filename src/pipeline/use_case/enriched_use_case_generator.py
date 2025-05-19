import os
import re
import textwrap

from pipeline.use_case.use_case_loader import UseCaseLoader
from pipeline.utils import (
    UserPersonaLoader, 
    Utils,
)


# ========== Step c: Prompt Constructor ==========
def build_scenario_prompt(
    uc,
    all_personas: dict,
    system_context: str,
    uc_guidelines: str,
    user_groups_guidelines: dict,
    previous_use_cases,
    proficiency_level: str = "",
) -> str:
    """Return a prompt that discourages scenario duplication."""

    # --- Current UC personas ---
    persona_blocks, group_set = [], set()
    for pid in uc.personas:
        if persona := all_personas.get(pid):
            persona_blocks.append(f"---\n{persona.to_prompt_string()}")
            group_set.add(persona.user_group)

    persona_text = "\n".join(persona_blocks)
    group_ctx = "\n\n".join(f"{g}:\n{user_groups_guidelines[g]}" for g in sorted(group_set))

    # --- Prior scenarios (last 6 for brevity) ---
    persona_by_id = {p.id: p for p in all_personas.values()}
    prev_summaries = []
    for prev in previous_use_cases:
        if not prev.scenario or prev.id == uc.id:
            continue
        actors = "; ".join(
            f"{persona_by_id[pid].name} ({persona_by_id[pid].role})"
            for pid in prev.personas if pid in persona_by_id
        )
        prev_summaries.append(f"- {prev.id} – {actors}\n{prev.scenario.strip()}")

    prev_block = "\n\n".join(prev_summaries[-6:]) or "None (The current is the first real use case being written, besides the non-existent examples)"

    return textwrap.dedent(
        f"""
You are a UX storyteller. Write a fresh, life-like, non-repetitive scenario for the provided use case of the following system.

--- SYSTEM CONTEXT ---
{system_context}

--- USER GROUP CONTEXT ---
Here are guidelines of user groups involved in this use case:
{group_ctx}

--- USE-CASE DEFINITION & NOT-REAL (NON-EXISTENT) EXAMPLES ---
{uc_guidelines}
-----------------------------

--- THE USE CASE (without life-like scenario) ---
Use Case ID: {uc.id}
Use Case Name: {uc.name}
Use Case Description: {uc.description}
Use Case Type: {uc.use_case_type}
Use Case Pillar(s): {', '.join(uc.pillars)}
Associated User Group(s): {', '.join(uc.user_groups)}
Involved Personas (actors):
{persona_text}
-----------------------------

--- YOUR TASK ---
Compose a lifelike 200–400-word scenario that:
  • Mentions *every* persona by name or role (not by ID)
  • Shows their motivations, interactions with given system, and the outcome
  • Does **not** copy or closely paraphrase any previous scenarios (both non-existent examples above and real ones below)
    • Strictly, the scenario must be **dominated by the unique traits, goals, pain-points, and behavioral biases of each involved persona**
    • If personas do have conflicting values or preferences (which usually do), **let the tension naturally emerge** — it is **encouraged** for the scenario to reflect this inconsistency or struggle
    • Do **not** smooth, or **rationalize** over differences between personas for the sake of system harmony — realism and contrast are more . I want the differences between multiple personas to be **visible** and **tangible** in the scenario
    • Avoid over-relying on the use case name or description, or the given system context or its user group summaries to dictate behavior. Focus instead on how these personas would realistically react, misunderstand, or personalize their experience with the system, using all their information provided in the persona context
-----------------------------

--- PREVIOUS REAL USE CASE SCENARIOS (To avoid duplication) ---
Besides the unreal and non-existent examples in the Use case Guidelines, here are the last scenarios of other use cases that has been written:
{prev_block}
Note that, while minor thematic similarities are acceptable, the current scenario must present clearly **distinct** actions, motivations, and interactions for the involved personas. Do not reuse **specific** activities, dialogue, or situation structures from prior scenarios—even implicitly. Focus on crafting a uniquely personalized and realistic narrative driven by the distinctive goals, traits, struggles, main actions, etc., of the personas involved in this use case.
When the current scenario includes a persona that has been previously used, it should be focused on the aspects of that persona (e.g., goals, actions, challenges, singularities, ...) that has not been previously used or presented. However, if there is no new aspects to use, just re-use the existing ones, strictly do not generate new aspects for each persona, as these aspects must always be presented all in the persona context.
-----------------------------

Strictly return only the scenario narrative. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.

{proficiency_level}

--- END OF PROMPT ---
"""
    ).strip()


# ========== Step c: Main Entry ==========
def enrich_use_cases_with_scenarios(persona_loader: UserPersonaLoader) -> None:
    """Fill the `scenario` field for each use case if missing, and name+desc are already present."""

    utils = Utils()

    all_personas = {p.id: p for p in persona_loader.get_personas()}
    uc_guidelines = utils.load_use_case_guidelines()
    system_context = utils.load_system_context()
    user_groups_guidelines = utils.load_all_user_group_descriptions()

    uc_loader = UseCaseLoader()
    uc_loader.load()
    
    # --- Language proficiency level ---
    proficiency_level = utils.load_llm_response_language_proficiency_level()

    for uc in uc_loader.get_all():
        if uc.scenario and uc.scenario.strip():
            print(f"⏭️  {uc.id} already has a scenario.")
            continue
        if not (uc.name and uc.description):
            print(f"⚠️  {uc.id} missing name or description – skipping.")
            continue

        print(f"\n🧠  Generating scenario for {uc.id} …")
        prompt = build_scenario_prompt(uc, all_personas, system_context, uc_guidelines, user_groups_guidelines, uc_loader.get_all())
        raw = utils.get_llm_response(prompt)

        # Clean accidental code fences or markdown
        scenario = re.sub(r"```.*?```", "", raw, flags=re.S).strip()
        uc.scenario = scenario

        print(f"✅  {uc.id} scenario added → {scenario[:200]}…")

    uc_loader.save_all()
    print("💾  Scenario generation complete.")
