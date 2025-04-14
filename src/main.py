import os
from use_case_generator import generate_raw_use_cases, enrich_use_cases_with_scenarios
from user_persona_loader import UserPersonaLoader
from use_case_loader import UseCaseLoader
from capability_blueprint_generator import generate_all_capability_blueprints
from capability_blueprint_analyzer import analyze_capability_blueprints
from user_story_generator import generate_user_stories_by_persona
from user_story_conflict_checker import check_user_story_conflicts, convert_conflict_jsons_to_csv
from utils import CURRENT_LLM, USE_CASE_DIR, FILTERED_CAPABILITY_BLUEPRINTS_DIR


def is_use_case_folder_empty(folder: str) -> bool:
    return not any(fname.endswith(".json") and fname.startswith("UC-") for fname in os.listdir(folder)) if os.path.exists(folder) else True

def main():
    # Step 1: Load user personas
    print("\n============================================================= LOAD USER PERSONAS =====================================================================")
    print("\n📁 Loading user personas...")
    persona_loader = UserPersonaLoader()
    persona_loader.load()
    # persona_loader.print_all_personas()

    # Step 2: Load/Generate use cases
    print("\n============================================================== LOAD / GENERATE USE CASES =============================================================")
    #   Step 2a: Check for use cases
    print("\n📁 Checking for existing use cases...")
    if is_use_case_folder_empty(USE_CASE_DIR):
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
    enrich_use_cases_with_scenarios(persona_loader)

    print("\n📋 Final Use Cases Summary:")
    use_case_loader = UseCaseLoader()
    use_case_loader.load()
    use_case_loader.print_all_use_cases()

    # Step 3: Load/Generate Capability Blueprints
    print("\n============================================================= CAPABILITY BLUEPRINTS ==================================================================")
    print("🚀 Starting ALFRED Capability Blueprints generation pipeline...")
    generate_all_capability_blueprints()

    # Step 4: Filter Capability Blueprints by Persona
    print("\n========================================================== CAPABILITY BLUEPRINT ANALYSIS =============================================================")
    analyze_capability_blueprints(persona_loader)

    # Step 5: Generate Persona-Based User Stories
    # print("\n============================================================ GENERATE USER STORIES ==================================================================")
    # print("🛠️ Generating user stories for each persona based on filtered Capability Blueprints, use cases, and ALFRED context...")
    # generate_user_stories_by_persona(persona_loader, use_case_loader)

    # print("\n✅ Pipeline completed successfully. Check your results in the output folder.")
    
    # Step 6: Analyze User Story Conflicts
    print("\n============================================================ USER STORY CONFLICT CHECK ===============================================================")
    print("🧠 Comparing user stories across personas for possible conflicts...")
    # check_user_story_conflicts()
    convert_conflict_jsons_to_csv("results/conflict_analysis")


if __name__ == "__main__":
    main()
