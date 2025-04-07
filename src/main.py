import os
from user_persona_loader import UserPersonaLoader
from use_case_generator import UseCaseGenerator, UseCaseLoader
from requirement_generator import RequirementGenerator, RequirementLoader
from requirement_comparator import RequirementComparator
from conflict_extractor import ConflictExtractor
from llm_handler import CURRENT_LLM

def main():
    print()
    print("======================================================================================================================================================") 
    print(f"======================================= SYSTEM REQUIREMENT GENERATOR — Using LLM: {CURRENT_LLM.upper()} ==========================================")
    print("======================================================================================================================================================") 

    print("\n============================================================= LOAD USER PERSONAS =====================================================================")
    persona_loader = UserPersonaLoader()
    persona_loader.load()
    personas = persona_loader.get_personas()

    if not personas:
        print("❌ No user personas found. Please add persona JSON files.")
        return

    print(f"\n📌 Loaded {len(personas)} personas:\n")
    for persona in personas:
        print("------------------------------------------------------------------------------------------------------------------------------------------------------")
        persona.display()

    print()
    print("============================================================== LOAD / GENERATE USE CASES =============================================================")

    use_case_folder = os.path.join("results", CURRENT_LLM, "use_cases")
    use_cases = []

    if os.path.exists(use_case_folder) and os.listdir(use_case_folder):
        print("📁 Existing use cases found — loading them...")
        use_case_loader = UseCaseLoader(use_case_dir=use_case_folder) 
        use_case_loader.load()
        use_cases = use_case_loader.get_use_cases()
    else:
        print("⚙️ No existing use cases found — generating new ones...")
        generator = UseCaseGenerator(personas)
        use_cases = generator.generate_use_cases(output_dir=use_case_folder)

    print(f"\n✅ {len(use_cases)} use case(s) ready.\n")
    for use_case in use_cases:
        print("------------------------------------------------------------------------------------------------------------------------------------------------------")
        use_case.display()

    print()
    print("============================================================= LOAD / GENERATE REQUIREMENTS ===========================================================")

    requirements_folder = os.path.join("results", CURRENT_LLM, "requirements")  
    requirements = {}

    if os.path.exists(requirements_folder) and os.listdir(requirements_folder):
        print("📁 Existing requirements found — loading them...")
        req_loader = RequirementLoader(folder=requirements_folder)
        requirements = req_loader.load()
    else:
        print("⚙️ No existing requirements found — generating new ones...")
        req_generator = RequirementGenerator(personas, use_cases)
        req_generator.generate_requirements(output_dir=requirements_folder)
        print("\n✅ Requirement generation complete.")
        req_loader = RequirementLoader(folder=requirements_folder)
        requirements = req_loader.load()

    print(f"\n✅ Loaded requirements for {len(requirements)} personas.\n")
    all_requirements = []
    for persona, reqs in requirements.items():
        print(f"------------------------------------------------------------------------------------------------------------------------------------------------------")
        print(f"👤 Requirements for {persona}:")
        all_requirements.extend(reqs)
        for r in reqs:
            print(f"   - [{r.id}] {r.name} ({r.type}) — Tags: {', '.join(r.tags)}")
            print(f"     ↳ Use Cases: {', '.join(r.use_cases)}")
            print(f"     ↳ {r.description}\n")

    print()     
    print("====================================================== REQUIREMENTS COMPARATIVE ANALYSIS ============================================================")
    merged_output_folder = os.path.join("results", CURRENT_LLM, "merged_requirements")
    comparator = RequirementComparator(requirements, output_dir=merged_output_folder)
    comparator.run()
    
    # Conflict Extraction
    print("\n========================================================== EXTRACT CONFLICTS TO CSV =================================================================")
    output_csv_path = os.path.join("results", CURRENT_LLM, "conflicts.csv")
    extractor = ConflictExtractor(requirements=all_requirements, personas=personas, merged_dir=merged_output_folder)
    extractor.extract_conflicts_to_csv(output_csv_path)

if __name__ == "__main__":
    main()
