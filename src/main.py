import os
from use_case_generator import generate_raw_use_cases, enrich_use_cases_with_scenarios
from user_persona_loader import UserPersonaLoader
from use_case_loader import UseCaseLoader
from raw_requirement_generator import generate_all_raw_requirements
from raw_requirement_loader import RawRequirementLoader
from user_story_generator import generate_user_stories_by_persona
from utils import CURRENT_LLM

USE_CASE_FOLDER = os.path.join("results", CURRENT_LLM, "use_cases")


def is_use_case_folder_empty(folder: str) -> bool:
    return not any(fname.endswith(".json") and fname.startswith("UC-") for fname in os.listdir(folder)) if os.path.exists(folder) else True

def main():
    # Step 1: Load user personas
    print("\n============================================================= LOAD USER PERSONAS =====================================================================")
    print("\n📁 Loading user personas...")
    persona_loader = UserPersonaLoader()
    persona_loader.load()
    persona_loader.print_all_personas()

    # Step 2: Load/Generate use cases
    print("\n============================================================== LOAD / GENERATE USE CASES =============================================================")
    #   Step 2a: Check for use cases
    print("\n📁 Checking for existing use cases...")
    if is_use_case_folder_empty(USE_CASE_FOLDER):
        print("📂 No use cases found. Starting generation process...")
        generate_raw_use_cases()
    else:
        print("📂 Existing use cases found. Loading from files...")
        use_case_loader = UseCaseLoader()
        use_case_loader.load()
        for uc in use_case_loader.get_all():
            print(f"✅ {uc.id} - {uc.name} ({uc.pillar})")
    
    #   Step 2b: Enrich with scenarios and personas (Phase 2)
    print("\n🔍 Beginning scenario enrichment...")
    enrich_use_cases_with_scenarios()
    
    print("\n📋 Final Use Cases Summary:")
    use_case_loader = UseCaseLoader()
    use_case_loader.load()
    use_case_loader.print_all_use_cases()
    
    # Step 3: Load/Generate Raw Requirements
    print("\n================================================================ RAW REQUIREMENTS ====================================================================")
    print("🚀 Starting ALFRED raw requirement generation pipeline...")
    generate_all_raw_requirements()

    # Step 4: Generate Persona-Based User Stories
    print("\n============================================================ GENERATE USER STORIES ==================================================================")
    print("🛠️ Generating user stories for each persona based on raw requirements, use cases, and ALFRED context...")
    requirement_loader = RawRequirementLoader()
    generate_user_stories_by_persona(persona_loader, requirement_loader, use_case_loader)
    
    print("\n✅ Pipeline completed successfully. Check your results in the output folder.")

if __name__ == "__main__":
    main()
