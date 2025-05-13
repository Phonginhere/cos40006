import sys
import random

from user_persona_loader import UserPersonaLoader
from use_cases.use_case_loader import UseCaseLoader
from use_cases.skeleton_use_case_writer import write_use_case_skeletons
from use_cases.raw_use_case_generator import generate_raw_use_cases
from use_cases.enriched_use_case_generator import enrich_use_cases_with_scenarios
from use_cases.use_case_task_analyzer import analyze_all_use_cases

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
    
    print("\n✅ Pipeline completed successfully. Check your results in the output folder.")

if __name__ == "__main__":
    main()
