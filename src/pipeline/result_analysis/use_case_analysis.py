import os
import pandas as pd
from collections import Counter

from pipeline.use_case.use_case_loader import UseCaseLoader
from pipeline.utils import Utils


def analyze_use_case_summary(uc_loader: "UseCaseLoader"):
    utils = Utils()
    use_cases = uc_loader.get_all()
    
    output_path = utils.USE_CASE_SUMMARY_ANALYSIS_CSV_FILE_PATH
    if os.path.exists(output_path):
        print(f"⚠️ {output_path} already exists. Please delete it to regenerate.")
        return

    records = []
    for uc in use_cases:
        records.append({
            "ID": uc.id,
            "Type": uc.use_case_type,
            "Personas": "\n".join(uc.personas),
            "User Groups": "\n".join(uc.user_groups),
            "Pillars": "\n".join(uc.pillars),
            "Title": uc.title,
        })

    df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ Use case summary saved to {output_path}")


def analyze_use_case_type_distribution(uc_loader: "UseCaseLoader"):
    utils = Utils()
    use_cases = uc_loader.get_all()
    
    output_path = utils.USE_CASE_TYPE_DISTRIBUTION_ANALYSIS_CSV_FILE_PATH
    if os.path.exists(output_path):
        print(f"⚠️ {output_path} already exists. Please delete it to regenerate.")
        return

    type_counter = Counter(uc.use_case_type for uc in use_cases)
    total = sum(type_counter.values())

    records = [
        {
            "Type": use_case_type,
            "Number of Use case": count,
            "Distribution Percentage": f"{(count / total) * 100:.0f}%"
        }
        for use_case_type, count in type_counter.items()
    ]

    # Add total row
    records.append({
        "Type": "Total",
        "Number of Use case": total,
        "Distribution Percentage": "100%"
    })

    df = pd.DataFrame(records)
    df.sort_values(by="Number of Use case", ascending=False, inplace=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ Use case type distribution saved to {output_path}")


def analyze_user_group_coverage(uc_loader: "UseCaseLoader"):
    utils = Utils()
    use_cases = uc_loader.get_all()
    
    output_path = utils.USE_CASE_USER_GROUP_COVERAGE_ANALYSIS_CSV_FILE_PATH
    if os.path.exists(output_path):
        print(f"⚠️ {output_path} already exists. Please delete it to regenerate.")
        return

    group_counter = Counter()
    for uc in use_cases:
        group_counter.update(uc.user_groups)

    total = len(use_cases)
    df = pd.DataFrame([
        {
            "User Group": group,
            "Number of appearances in all use cases": count,
            "Coverage Percentage": f"{(count / total) * 100:.0f}%"
        }
        for group, count in group_counter.items()
    ])
    df.sort_values(by="Number of appearances in all use cases", ascending=False, inplace=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ User group coverage saved to {output_path}")


def analyze_persona_coverage(uc_loader: "UseCaseLoader"):
    utils = Utils()
    use_cases = uc_loader.get_all()
    
    output_path = utils.USE_CASE_PERSONA_COVERAGE_ANALYSIS_CSV_FILE_PATH
    if os.path.exists(output_path):
        print(f"⚠️ {output_path} already exists. Please delete it to regenerate.")
        return

    persona_counter = Counter()
    for uc in use_cases:
        persona_counter.update(uc.personas)

    total = len(use_cases)
    df = pd.DataFrame([
        {
            "Persona": pid,
            "Number of appearances in all use cases": count,
            "Coverage Percentage": f"{(count / total) * 100:.0f}%"
        }
        for pid, count in persona_counter.items()
    ])
    df.sort_values(by="Number of appearances in all use cases", ascending=False, inplace=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ Persona coverage saved to {output_path}")
