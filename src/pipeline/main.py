import sys
import time
import random

from pipeline.utils import UserPersonaLoader

from pipeline.use_case.use_case_loader import UseCaseLoader
from pipeline.use_case.skeleton_use_case_randomizer import write_use_case_skeletons
from pipeline.use_case.raw_use_case_generator import generate_raw_use_cases
from pipeline.use_case.enriched_use_case_generator import enrich_use_cases_with_scenarios
from pipeline.use_case.use_case_task_extractor import extract_tasks_from_all_use_cases
from pipeline.use_case.use_case_task_deduplicator import deduplicate_tasks_for_all_use_cases

from pipeline.user_story.user_story_loader import UserStoryLoader
from pipeline.user_story.skeleton_user_story_extractor import extract_skeleton_user_stories
from pipeline.user_story.user_story_generator import generate_complete_user_stories
from pipeline.user_story.user_story_deduplicator import deduplicate_user_stories_for_each_persona
from pipeline.user_story.user_story_persona_centric_verifier import verify_user_stories_to_ensure_persona_centricity
from pipeline.user_story.user_story_functional_and_non_funtional_typer import update_user_stories_with_type
from pipeline.user_story.non_functional_user_story_clusterer import cluster_non_functional_user_stories
from pipeline.user_story.functional_user_story_clusterer import generate_functional_cluster_definitions, cluster_functional_user_stories

from pipeline.user_story_conflict.user_story_conflict_verifier import verify_conflicts
from pipeline.user_story_conflict.non_functional_user_story_decomposer import decompose_non_functional_user_stories
from pipeline.user_story_conflict.non_functional_user_story_conflict_within_one_group_identifier import identify_non_functional_conflicts_within_one_group
from pipeline.user_story_conflict.non_functional_user_story_conflict_within_one_group_resolver import resolve_non_functional_conflicts_within_one_group
from pipeline.user_story_conflict.non_functional_user_story_conflict_across_two_groups_identifier import identify_non_functional_conflicts_across_two_groups
from pipeline.user_story_conflict.non_functional_user_story_conflict_across_two_groups_resolver import resolve_non_functional_conflicts_across_two_groups 

from pipeline.user_story_conflict.functional_user_story_conflict_within_one_group_identifier import identify_functional_conflicts_within_one_group
from pipeline.user_story_conflict.functional_user_story_conflict_within_one_group_resolver import resolve_functional_conflicts_within_one_group
from pipeline.user_story_conflict.functional_user_story_conflict_across_two_groups_identifier import identify_functional_conflicts_across_two_groups
from pipeline.user_story_conflict.functional_user_story_conflict_across_two_groups_resolver import resolve_functional_conflicts_across_two_groups

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
    extract_tasks_from_all_use_cases(persona_loader)
    
    #   Step 2e: Deduplicate tasks for each persona
    print("\n🔄 Phase 2e: Deduplicating tasks for each persona...")
    deduplicate_tasks_for_all_use_cases(persona_loader)
    
    # Step 3: Generate user stories from tasks
    print("\n============================================================ LOAD / GENERATE USER STORIES ============================================================")
    user_story_loader = UserStoryLoader()
    
    #   Step 3a: Generate skeleton user stories from tasks
    print("\n📘 Phase 3a: Generating skeleton user stories from extracted tasks...")
    extract_skeleton_user_stories(persona_loader)
    
    #   Step 3b: Generate complete user stories from skeletons
    print("\n📝 Phase 3b: Generating complete user stories...")
    generate_complete_user_stories(persona_loader, use_case_loader)
    
    #   Step 3b-1: Verify user story summaries for persona dominance
    print("\n🔎 Phase 3b-1: Verifying user story summaries for persona dominance...")
    verify_user_stories_to_ensure_persona_centricity(persona_loader)
    
    #   Step 3c: Update user stories with type (functional/non-functional)
    print("\n🔍 Phase 3c: Updating user stories with type...")
    update_user_stories_with_type()
    
    #   Step 3d: Cluster non-functional user stories
    print("\n🗂️ Phase 3d: Clustering non-functional user stories...")
    cluster_non_functional_user_stories(user_story_loader)
    
    #       Optional: Summary output for verification
    print("\n📊 Phase 3d-1: Summary of clustered non-functional user stories...")
    user_story_loader.load_all_user_stories()
    user_story_loader.print_clusters_for_non_functional_stories()
    
    #   Step 3e: Cluster functional user stories (based on non-functional clusters)
    #       Step 3e-1: Generate functional user story cluster set   
    print("\n🧠 Phase 3e-1: Generating functional user story cluster set...")
    generate_functional_cluster_definitions()
    
    #       Step 3e-2: Cluster functional user stories
    print("\n📦 Phase 3e-2: Clustering functional user stories...")
    cluster_functional_user_stories(user_story_loader)
    
    #       Optional: Summary output for verification
    print("\n📊 Phase 3e-3: Summary of clustered functional user stories...")
    user_story_loader.load_all_user_stories()
    user_story_loader.print_clusters_for_functional_stories()
    
    #   Step 3f: Deduplicate user stories for each persona within each cluster
    print("\n🗂️ Phase 3f: Deduplicating user stories for each persona within each cluster...")
    deduplicate_user_stories_for_each_persona(persona_loader)
    
    # Step 4: Conflict analysis for non-functional user stories within one user group
    print("\n============================================================ ANALYZE NON-FUNCTIONAL USER STORIES WITHIN ONE USER GROUP ====================================")
    #   Step 4a: Decomposite non-functional user stories
    print("\n🔍 Phase 4a: Decompositing non-functional user stories...")
    decompose_non_functional_user_stories(user_story_loader)
    
    #   Step 4b: Identify conflicts within one user group
    print("\n⚔️ Phase 4b: Identifying conflicts for non-functional user stories within one user group...")
    identify_non_functional_conflicts_within_one_group(user_story_loader)
    
    #       Step 4b-1: Verify conflicts for non-functional user stories within one user group
    print("\n🔍 Phase 4b-1: Verifying conflicts for non-functional user stories within one user group...")
    verify_conflicts(persona_loader, functional=False)
    
    #   Step 4c: Resolve conflicts within one user group
    print("\n🛠️ Phase 4c: Resolving conflicts for non-functional user stories within one user group...")
    resolve_non_functional_conflicts_within_one_group(persona_loader)
    
    # Step 5: Conflict analysis for non-functional user stories across two user groups
    print("\n============================================================ ANALYZE NON-FUNCTIONAL USER STORIES ACROSS TWO USER GROUPS ====================================")
    #   Step 5a: Identify conflicts across two user groups
    print("\n⚔️ Phase 5a: Identifying conflicts for non-functional user stories across two user groups...")
    identify_non_functional_conflicts_across_two_groups(user_story_loader)
    
    #       Step 5a-1: Verify conflicts for non-functional user stories across two user groups
    print("\n🔍 Phase 5a-1: Verifying conflicts for non-functional user stories across two user groups...")
    verify_conflicts(persona_loader, functional=False, within_one_group=False)
    
    #  Step 5b: Resolve conflicts across two user groups
    print("\n🛠️ Phase 5b: Resolving conflicts for non-functional user stories across two user groups...")
    resolve_non_functional_conflicts_across_two_groups(persona_loader)
    
    # Step 6: Conflict analysis for functional user stories within one user group
    print("\n============================================================ ANALYZE FUNCTIONAL USER STORIES WITHIN ONE USER GROUP ====================================")
    #   Step 6a: Identify conflicts within one user group
    print("\n⚔️ Phase 6a: Identifying conflicts for functional user stories within one user group...")
    identify_functional_conflicts_within_one_group(user_story_loader)
    
    #      Step 6a-1: Verify conflicts for functional user stories within one user group
    print("\n🔍 Phase 6a-1: Verifying conflicts for functional user stories within one user group...")
    verify_conflicts(persona_loader, functional=True)
    
    #   Step 6b: Resolve conflicts within one user group
    print("\n🛠️ Phase 6b: Resolving conflicts for functional user stories within one user group...")
    resolve_functional_conflicts_within_one_group(persona_loader)
    
    # Step 7: Conflict analysis for functional user stories across two user groups
    print("\n============================================================ ANALYZE FUNCTIONAL USER STORIES ACROSS TWO USER GROUPS ====================================")
    #   Step 7a: Identify conflicts across two user groups
    print("\n⚔️ Phase 7a: Identifying conflicts for functional user stories across two user groups...")
    identify_functional_conflicts_across_two_groups(user_story_loader)
    
    #       Step 7a-1: Verify conflicts for functional user stories across two user groups
    print("\n🔍 Phase 7a-1: Verifying conflicts for functional user stories across two user groups...")
    verify_conflicts(persona_loader, functional=True, within_one_group=False)
    
    #   Step 7b: Resolve conflicts across two user groups
    print("\n🛠️ Phase 7b: Resolving conflicts for functional user stories across two user groups...")
    resolve_functional_conflicts_across_two_groups(persona_loader)
    
    print("\n✅ Pipeline completed successfully. Check your results in the output folder.")

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    elapsed = end_time - start_time
    minutes, seconds = divmod(elapsed, 60)
    print(f"\n⏱️ Total pipeline runtime: {int(minutes)} min {int(seconds)} sec ({elapsed:.2f} seconds)")

