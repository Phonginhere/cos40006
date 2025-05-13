def build_scenario_prompt(
    current_use_case: UseCase,
    persona_infos: List[str],
    previous_use_cases: List[UseCase],
    persona_by_id: dict
) -> str:
    alfred_summary = load_alfred_summary()

    previous_summaries = []
    for prev_uc in previous_use_cases:
        if not prev_uc.scenario:
            continue

        # Build persona context for the previous use case
        persona_descriptions = []
        for pid in prev_uc.personas or []:
            persona = persona_by_id.get(pid)
            if persona:
                persona_descriptions.append(f"{persona.name} ({persona.role}) – {persona.tagline}")
        
        involved_desc = "; ".join(persona_descriptions) or "Unknown personas"
        scenario_trimmed = prev_uc.scenario.replace("\n", " ").strip()[:300]
        previous_summaries.append(f"- UC {prev_uc.id}: {involved_desc}\n  Scenario: {scenario_trimmed}...")

    previous_block = "\n\n".join(previous_summaries) if previous_summaries else "None"

    persona_block = "\n".join(f"---\n{info}" for info in persona_infos)

    return f"""
You are writing a lifelike usage scenario for the ALFRED system.

--- ALFRED SYSTEM SUMMARY ---
{alfred_summary}
-----------------------------

Below is an example scenario. It is only for the use case "Effective and Personalized Care". The example is provided to show the tone, structure, and depth expected in your writing. **Do not rely on its content**.

---
Personas: Otto the Older Person and Mike from the Medical Staff

Scenario: 
Mike from the Medical Staff has been caring for Otto, an older adult with mildly high blood pressure. To improve Otto’s care and provide peace of mind, they decide to use the ALFRED system along with a smart shirt that tracks vital signs like heart rate, temperature, breathing, and activity. This data is shared with Mike through ALFRED, while Otto stays in control of what’s shared and can view his own stats. He appreciates the privacy settings and wants the shirt to look stylish, not medical. ALFRED also reminds him to take his pills, and he confirms once he has. Occasionally, Mike checks in via video call, ensuring Otto is doing well, especially since he doesn’t have much social interaction. Together, ALFRED helps maintain Otto’s independence while supporting more effective and personalized care.
---

-----------------------------

Additionally, below are previously generated ALFRED use case scenarios. For each one, the involved personas are listed along with a short description. Please use this as background to ensure your new scenario does **not repeat** any previously written stories:
(Note that, some of following use case scenarios are trimmed due to the reduction of token overload)

{previous_block}

Now, please generate a scenario for a different use case and its involved personas:

Use Case:
ID: {use_case.id}
Pillar: {use_case.pillar}
Name: {use_case.name}
Description: {use_case.description}

Involved Personas:
{persona_block}

Write a grounded, practical, human-centered scenario showing how these individuals interact with ALFRED to fulfill this use case. Be realistic and detailed — include motivations, interactions, day-to-day context, and outcomes.

Return only the scenario narrative. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""

def enrich_use_cases_with_scenarios(persona_loader: UserPersonaLoader):
    print("\n🔄 Phase 3: Enriching use cases with SCENARIOS...")

    use_case_loader = UseCaseLoader()
    use_case_loader.load()
    use_cases = use_case_loader.get_all()

    all_personas = persona_loader.get_personas()
    persona_by_id = {p.id: p for p in all_personas}

    previous_use_cases_with_scenarios: list[UseCase] = []
    enriched_count = 0

    for use_case in use_cases:
        if use_case.scenario and use_case.scenario.strip():
            print(f"⏭️ Skipping {use_case.id} — already has a scenario.")
            previous_use_cases_with_scenarios.append(use_case)
            continue

        if not use_case.personas:
            print(f"⚠️ Skipping {use_case.id} — missing persona IDs.")
            continue

        valid_personas = [persona_by_id[pid] for pid in use_case.personas if pid in persona_by_id]
        if not valid_personas:
            print(f"⚠️ Skipping {use_case.id} — none of the persona IDs are valid.")
            continue

        persona_infos = [p.to_prompt_string() for p in valid_personas]
        scenario_prompt = build_scenario_prompt(
            use_case,
            persona_infos,
            previous_use_cases_with_scenarios,
            persona_by_id
        )

        print(f"🧠 Requesting scenario for {use_case.id}...")
        scenario_text = get_llm_response(scenario_prompt)

        if scenario_text and isinstance(scenario_text, str) and len(scenario_text.strip()) > 30:
            use_case.scenario = scenario_text.strip()
            previous_use_cases_with_scenarios.append(use_case)
            print(f"✅ Scenario added to {use_case.id}")
            enriched_count += 1
        else:
            use_case.scenario = "Scenario could not be generated."
            print(f"⚠️ Scenario failed for {use_case.id}")

    use_case_loader.save_all()
    print(f"✅ Finished enriching {enriched_count} new scenarios.")