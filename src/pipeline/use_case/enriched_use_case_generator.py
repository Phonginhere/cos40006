import os
import re
import textwrap

from pipeline.utils import get_llm_response, load_system_summary, load_use_case_summary, load_all_user_group_summaries
from pipeline.user_persona_loader import UserPersonaLoader
from pipeline.use_case.use_case_loader import UseCaseLoader


# ========== Step c: Prompt Constructor ==========
def build_scenario_prompt(
    uc,
    all_personas: dict,
    system_summary: str,
    uc_summary: str,
    group_summaries: dict,
    previous_use_cases,
) -> str:
    """Return a prompt that discourages scenario duplication."""

    # --- Current UC personas ---
    persona_blocks, group_set = [], set()
    for pid in uc.personas:
        if persona := all_personas.get(pid):
            persona_blocks.append(f"---\n{persona.to_prompt_string()}")
            group_set.add(persona.user_group)

    persona_text = "\n".join(persona_blocks)
    group_ctx = "\n\n".join(f"{g}:\n{group_summaries[g]}" for g in sorted(group_set))

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
        snippet = prev.scenario.replace("\n", " ").strip()[:250]
        prev_summaries.append(f"- {prev.id} – {actors}\n  {snippet}…")

    prev_block = "\n\n".join(prev_summaries[-6:]) or "None"

    return textwrap.dedent(
        f"""
You are a UX storyteller. Write a fresh, life-like, non-repetitive scenario for the provided use case of the following system.

--- SYSTEM SUMMARY ---
{system_summary}

--- USER GROUP CONTEXT ---
Here are summaries of user groups involved in this use case:
{group_ctx}

--- USE-CASE DEFINITION & NOT-REAL EXAMPLES ---
{uc_summary}
-----------------------------

--- THE USE CASE ---
Use Case ID: {uc.id}
Use Case Name: {uc.name}
Use Case Description: {uc.description}
Use Case Type: {uc.use_case_type}
Use Case Pillar(s): {', '.join(uc.pillars)}
Associated User Group(s): {', '.join(uc.user_groups)}
Involved Personas (actors):
{persona_text}

TASK → Compose a lifelike 200–400-word scenario that:
  • Mentions *every* persona by name or role (not by ID)
  • Shows their motivations, interactions with given system, and the outcome
  • Does **not** copy or closely paraphrase any previous scenario above
    • Strictly, the scenario must be **dominated by the unique traits, goals, pain-points, and behavioral biases of each involved persona**
    • If personas do have conflicting values or preferences (which usually do), **let the tension naturally emerge** — it is **encouraged** for the scenario to reflect this inconsistency or struggle
    • Do **not** smooth, or **rationalize** over differences between personas for the sake of system harmony — realism and contrast are more . I want the differences between multiple personas to be **visible** and **tangible** in the scenario
    • Avoid over-relying on the use case name or description, or the given system context or its user group summaries to dictate behavior. Focus instead on how these personas would realistically react, misunderstand, or personalize their experience with the system

Strictly return only the scenario narrative. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""
    ).strip()


# ========== Step c: Main Entry ==========
def enrich_use_cases_with_scenarios(persona_loader: UserPersonaLoader) -> None:
    """Fill the `scenario` field for each use case if missing, and name+desc are already present."""

    all_personas = {p.id: p for p in persona_loader.get_personas()}
    uc_summary = load_use_case_summary()
    system_summary = load_system_summary()
    group_summaries = load_all_user_group_summaries()

    uc_loader = UseCaseLoader()
    uc_loader.load()

    for uc in uc_loader.get_all():
        if uc.scenario and uc.scenario.strip():
            print(f"⏭️  {uc.id} already has a scenario.")
            continue
        if not (uc.name and uc.description):
            print(f"⚠️  {uc.id} missing name or description – skipping.")
            continue

        print(f"\n🧠  Generating scenario for {uc.id} …")
        prompt = build_scenario_prompt(uc, all_personas, system_summary, uc_summary, group_summaries, uc_loader.get_all())
        raw = get_llm_response(prompt)

        # Clean accidental code fences or markdown
        scenario = re.sub(r"```.*?```", "", raw, flags=re.S).strip()
        uc.scenario = scenario

        print(f"✅  {uc.id} scenario added → {scenario[:200]}…")

    uc_loader.save_all()
    print("💾  Scenario generation complete.")
