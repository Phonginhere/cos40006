import os
from user_persona_loader import UserPersonaLoader
from use_case_generator import UseCaseGenerator, UseCaseLoader
from requirement_generator import RequirementGenerator, RequirementLoader
from requirement_comparator import RequirementComparator

def main():
    """
    Main function to load user personas, generate or load use cases, and generate requirements.
    """

    print()
    print("======================================================================================================================================================") 
    print("============================================================= LOAD USER PERSONAS =====================================================================")
    
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
    print("======================================================================================================================================================") 
    print("============================================================== LOAD / GENERATE USE CASES =============================================================")

    use_case_folder = r"results\use_cases"
    use_cases = []

    if os.path.exists(use_case_folder) and os.listdir(use_case_folder):
        print("📁 Existing use cases found — loading them...")
        use_case_loader = UseCaseLoader()
        use_case_loader.load()
        use_cases = use_case_loader.get_use_cases()
    else:
        print("⚙️ No existing use cases found — generating new ones...")
        generator = UseCaseGenerator(personas)
        use_cases = generator.generate_use_cases()

    print(f"\n✅ {len(use_cases)} use case(s) ready.\n")
    for use_case in use_cases:
        print("------------------------------------------------------------------------------------------------------------------------------------------------------")
        use_case.display()

    print()
    print("======================================================================================================================================================") 
    print("============================================================= LOAD / GENERATE REQUIREMENTS ===========================================================")

    requirements = {}
    requirements_folder = r"results/requirements"

    if os.path.exists(requirements_folder) and os.listdir(requirements_folder):
        print("📁 Existing requirements found — loading them...")
        req_loader = RequirementLoader()
        requirements = req_loader.load()
    else:
        print("⚙️ No existing requirements found — generating new ones...")
        req_generator = RequirementGenerator(personas, use_cases)
        req_generator.generate_requirements()
        print("\n✅ Requirement generation complete. All results saved to 'results/requirements/'")
        req_loader = RequirementLoader()
        requirements = req_loader.load()

    print(f"\n✅ Loaded requirements for {len(requirements)} personas.\n")
    for persona, reqs in requirements.items():
        print(f"------------------------------------------------------------------------------------------------------------------------------------------------------")
        print(f"👤 Requirements for {persona}:")
        for r in reqs:
            print(f"   - [{r.id}] {r.name} ({r.type}) — Tags: {', '.join(r.tags)}")
            print(f"     ↳ Use Cases: {', '.join(r.use_cases)}")
            print(f"     ↳ {r.description}\n")
       
    print()     
    print("======================================================================================================================================================") 
    print("====================================================== REQUIREMENTS COMPARATIVE ANALYSIS ============================================================")
    
    comparator = RequirementComparator(requirements)
    comparator.run(["User_Interaction"])


if __name__ == "__main__":
    main()
