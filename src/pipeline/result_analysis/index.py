from pipeline.result_analysis.persona_analysis import analyze_personas
from pipeline.result_analysis.use_case_analysis import (
    analyze_use_case_summary,
    analyze_use_case_type_distribution,
    analyze_user_group_coverage,
    analyze_persona_coverage,
)
from pipeline.result_analysis.use_case_task_analysis import (
    analyze_use_case_task_extraction_and_deduplication,
    analyze_task_distribution_by_use_case_and_persona,
)
from pipeline.result_analysis.user_story_analysis import (
    analyze_user_story_uniqueness_by_personas_summary,
    analyze_user_story_uniqueness_by_type_summary,
    analyze_user_story_clustering_by_type
)
from pipeline.result_analysis.user_story_conflict_analysis import (
    analyze_all_conflict_verification_cases,
    analyze_and_flatten_all_conflict_verification_records,
    analyze_all_valid_conflict_resolutions_for_human_review
)

from pipeline.utils import UserPersonaLoader, Utils
from pipeline.use_case.use_case_loader import UseCaseLoader

def main(persona_loader: UserPersonaLoader = None, uc_loader: UseCaseLoader = None):
    # Initialize loaders
    if not persona_loader:
        persona_loader = UserPersonaLoader(no_logging=True)
        persona_loader.load()
    if not uc_loader:
        uc_loader = UseCaseLoader()
    
    uc_loader.load()

    # Perform analyses
    analyze_personas(persona_loader)
    analyze_use_case_summary(uc_loader)
    analyze_use_case_type_distribution(uc_loader)
    analyze_user_group_coverage(uc_loader)
    analyze_persona_coverage(uc_loader)
    analyze_use_case_task_extraction_and_deduplication()
    analyze_task_distribution_by_use_case_and_persona()
    analyze_user_story_uniqueness_by_personas_summary()
    analyze_user_story_uniqueness_by_type_summary()
    analyze_user_story_clustering_by_type("Functional")
    analyze_user_story_clustering_by_type("Non-Functional")
    
    analyze_all_conflict_verification_cases()
    analyze_and_flatten_all_conflict_verification_records()
    analyze_all_valid_conflict_resolutions_for_human_review()
    
if __name__ == "__main__":
    main()