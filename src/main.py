import sys
import random

from user_persona_loader import UserPersonaLoader

from use_cases.use_case_loader import UseCaseLoader
from use_cases.skeleton_use_case_writer import write_use_case_skeletons
from use_cases.raw_use_case_generator import generate_raw_use_cases
from use_cases.enriched_use_case_generator import enrich_use_cases_with_scenarios
from use_cases.use_case_task_analyzer import analyze_all_use_cases

from user_stories.skeleton_user_story_extractor import extract_skeleton_user_stories
from user_stories.user_story_generator import generate_complete_user_stories
from user_stories.user_story_fr_nfr_typer import update_user_stories_with_type

def main():
    # Step 1: Load user personas
    print("\n============================================================= LOAD USER PERSONAS =====================================================================")
    print("\n📁 Phase 1: Loading user personas...")
    persona_loader = UserPersonaLoader()
    persona_loader.load()
    # persona_loader.print_all_personas()

    # Step 2: Load/Generate use cases
    print("\n============================================================== LOAD / GENERATE USE CASES =============================================================")
    #   Step 2a: Write use case skeletons
    print("\n📁 Phase 2a: Checking for existing skeletons or writing new ones...")
    write_use_case_skeletons(persona_loader, seed=42)
    
    #   Step 2b: Generate raw use case content (name + description)
    print("\n🛠️ Phase 2b: Generating raw use case content...")
    generate_raw_use_cases(persona_loader)
    
    #   Step 2c: Enrich raw use cases with life-like scenarios
    print("\n🎭 Phase 2c: Enriching use cases with scenarios...")
    enrich_use_cases_with_scenarios(persona_loader)

    print("\n📋 Final Use Cases Summary:")
    use_case_loader = UseCaseLoader()
    use_case_loader.load()
    # use_case_loader.print_all_use_cases()
    print(f"✅ Loaded {len(use_case_loader.get_all())} use cases.")
    
    #   Step 2d: Extract persona tasks from scenarios
    print("\n🧾 Phase 2d: Extracting tasks from scenarios...")
    analyze_all_use_cases(persona_loader)
    
    # Step 3: Generate user stories from tasks
    print("\n============================================================ LOAD / GENERATE USER STORIES ============================================================")
    #   Step 3a: Generate skeleton user stories from tasks
    print("\n📘 Phase 3a: Generating skeleton user stories from extracted tasks...")
    extract_skeleton_user_stories(persona_loader)
    
    #   Step 3b: Generate complete user stories from skeletons
    print("\n📝 Phase 3b: Generating complete user stories...")
    generate_complete_user_stories(persona_loader, use_case_loader)
    
    #   Step 3c: Update user stories with type (functional/non-functional)
    print("\n🔍 Phase 3c: Updating user stories with type...")
    update_user_stories_with_type()
    
    print("\n✅ Pipeline completed successfully. Check your results in the output folder.")

if __name__ == "__main__":
    main()
