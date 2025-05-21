import os
import json

import pandas as pd
from collections import defaultdict
from pathlib import Path

from pipeline.utils import Utils

def analyze_conflict_verification(valid_dir, invalid_dir, output_csv_path, conflict_type: str, is_across_groups: bool):
    utils = Utils()
    
    if os.path.exists(output_csv_path):
        print(f"⚠️ {output_csv_path} already exists. Please delete it to re-generate.")
        return
    
    group_keys = utils.load_user_group_keys()  # {"Group Name": "UG-001"}
    key_to_name = {v.replace("-", "_"): k for k, v in group_keys.items()}  # {"UG_001": "Group Name"}

    # Determine number of groups and group-pairs
    n = len(group_keys)
    m = int(n * (n - 1) / 2)

    valid_counts = defaultdict(int)
    invalid_counts = defaultdict(int)

    # Count from valid folder
    for file in Path(valid_dir).glob("*.json"):
        with open(file, encoding="utf-8") as f:
            data = json.load(f)
        group_key = file.stem.replace("UG-", "UG_").replace("-", "_")
        group_name = get_group_label(group_key, key_to_name, is_across_groups)
        valid_counts[group_name] += len(data)

    # Count from invalid folder
    for file in Path(invalid_dir).glob("*.json"):
        with open(file, encoding="utf-8") as f:
            data = json.load(f)
        group_key = file.stem.replace("UG-", "UG_").replace("-", "_")
        group_name = get_group_label(group_key, key_to_name, is_across_groups)
        invalid_counts[group_name] += len(data)

    all_groups = set(valid_counts.keys()) | set(invalid_counts.keys())
    records = []
    total_verified = 0
    total_failed = 0

    for group in sorted(all_groups):
        verified = valid_counts[group]
        failed = invalid_counts[group]
        total = verified + failed
        percent = f"{round((verified / total) * 100) if total > 0 else 0}%"

        total_verified += verified
        total_failed += failed

        records.append({
            ("User Group" if not is_across_groups else "User Group Pair"): group,
            "Total Number of Identified Conflicts": total,
            "Number of Identified Conflicts successfully Verified": verified,
            "Number of Identified Conflicts that failed Verification": failed,
            "Conflict Verification Success Rate": percent,
        })

    records.append({
        ("User Group" if not is_across_groups else "User Group Pair"): "Total",
        "Total Number of Identified Conflicts": total_verified + total_failed,
        "Number of Identified Conflicts successfully Verified": total_verified,
        "Number of Identified Conflicts that failed Verification": total_failed,
        "Conflict Verification Success Rate": f"{round((total_verified / (total_verified + total_failed)) * 100) if (total_verified + total_failed) > 0 else 0}%",
    })

    df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")
    print(f"✅ Conflict verification summary ({conflict_type}) saved to {output_csv_path}")

def get_group_label(key, key_to_name, is_pair):
    if is_pair:
        # e.g., UG_001_vs_UG_002
        parts = key.replace("UG-", "UG_").split("_vs_")
        g1 = key_to_name.get(parts[0], parts[0])
        g2 = key_to_name.get(parts[1], parts[1])
        return f"{g1} vs {g2}"
    else:
        return key_to_name.get(key.replace("-", "_"), key)

def analyze_all_conflict_verification_cases():
    utils = Utils()

    analyze_conflict_verification(
        utils.FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
        utils.INVALID_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
        utils.FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_VERIFYING_ANALYSIS_CSV_FILE_PATH,
        "Functional within-group",
        is_across_groups=False,
    )

    analyze_conflict_verification(
        utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
        utils.INVALID_NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
        utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_VERIFYING_ANALYSIS_CSV_FILE_PATH,
        "Non-Functional within-group",
        is_across_groups=False,
    )

    analyze_conflict_verification(
        utils.FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
        utils.INVALID_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
        utils.FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_VERIFYING_ANALYSIS_CSV_FILE_PATH,
        "Functional across-groups",
        is_across_groups=True,
    )

    analyze_conflict_verification(
        utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
        utils.INVALID_NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
        utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_VERIFYING_ANALYSIS_CSV_FILE_PATH,
        "Non-Functional across-groups",
        is_across_groups=True,
    )

def analyze_and_flatten_all_conflict_verification_records():
    utils = Utils()
    output_path = utils.USER_STORY_CONFLICT_VERIFICATION_ANALYSIS_BY_HUMAN_CSV_FILE_PATH
    
    if os.path.exists(output_path):
        print(f"⚠️ {output_path} already exists. Please delete it to re-generate.")
        return

    # Define all conflict types with associated folders and metadata
    conflict_sources = [
        {
            "name": "Non-Functional within-group",
            "valid_dir": utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
            "invalid_dir": utils.INVALID_NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
            "is_across_groups": False
        },
        {
            "name": "Functional within-group",
            "valid_dir": utils.FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
            "invalid_dir": utils.INVALID_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
            "is_across_groups": False
        },
        {
            "name": "Non-Functional across-groups",
            "valid_dir": utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
            "invalid_dir": utils.INVALID_NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
            "is_across_groups": True
        },
        {
            "name": "Functional across-groups",
            "valid_dir": utils.FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
            "invalid_dir": utils.INVALID_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
            "is_across_groups": True
        },
    ]

    all_records = []

    for source in conflict_sources:
        for is_valid, folder in [(True, source["valid_dir"]), (False, source["invalid_dir"])]:
            for file in Path(folder).glob("*.json"):
                try:
                    with open(file, encoding="utf-8") as f:
                        conflicts = json.load(f)
                except Exception as e:
                    print(f"❌ Failed to read {file.name}: {e}")
                    continue

                for c in conflicts:
                    try:
                        record = {
                            "ID": c.get("conflictId", ""),
                            "Personas": f"{c.get('personaAId', '')},\n{c.get('personaBId', '')}",
                            "User Group(s)": (
                                f"{c.get('userGroup', '')}"
                                if not source["is_across_groups"]
                                else f"{c.get('userGroupA', '')},\n{c.get('userGroupB', '')}"
                            ),
                            "User Stories": f"\n{c.get('userStoryASummary', '')},\n{c.get('userStoryBSummary', '')}",
                            "LLM Long-prompt identified": "CONFLICT",
                            "LLM Short-prompt verified": (
                                "CONFLICT" if is_valid else "INVALID CONFLICT\n(NO CONFLICT)"
                            ),
                            "Human verified (by the team)": "",
                            "LLM and Human Verification Match": "",
                        }
                        all_records.append(record)
                    except Exception as e:
                        print(f"⚠️ Failed to parse a conflict in {file.name}: {e}")

    # Save to DataFrame
    df = pd.DataFrame(all_records)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ Flattened conflict verification records saved to {output_path}")


def analyze_all_valid_conflict_resolutions_for_human_review():
    utils = Utils()
    output_path = utils.USER_STORY_CONFLICT_RESOLUTION_ANALYSIS_BY_HUMAN_CSV_FILE_PATH
    
    if os.path.exists(output_path):
        print(f"⚠️ {output_path} already exists. Please delete it to re-generate.")
        return

    # Conflict resolution sources: VALID files only
    resolution_sources = [
        {
            "name": "Non-Functional within-group",
            "valid_dir": utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
            "is_across_groups": False
        },
        {
            "name": "Functional within-group",
            "valid_dir": utils.FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
            "is_across_groups": False
        },
        {
            "name": "Non-Functional across-groups",
            "valid_dir": utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
            "is_across_groups": True
        },
        {
            "name": "Functional across-groups",
            "valid_dir": utils.FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
            "is_across_groups": True
        },
    ]

    all_records = []

    for source in resolution_sources:
        for file in Path(source["valid_dir"]).glob("*.json"):
            try:
                with open(file, encoding="utf-8") as f:
                    conflicts = json.load(f)
            except Exception as e:
                print(f"❌ Failed to read {file.name}: {e}")
                continue

            for c in conflicts:
                try:
                    record = {
                        "ID": c.get("conflictId", ""),
                        "Personas": f"{c.get('personaAId', '')},\n{c.get('personaBId', '')}",
                        "User Group(s)": (
                            f"{c.get('userGroup', '')}"
                            if not source["is_across_groups"]
                            else f"{c.get('userGroupA', '')},\n{c.get('userGroupB', '')}"
                        ),
                        "Old User Stories": f"\n{c.get('userStoryASummary', '')},\n{c.get('userStoryBSummary', '')}",
                        "New User Stories": f"\n{c.get('newUserStoryASummary', '')},\n{c.get('newUserStoryBSummary', '')}",
                        "Agreed by human (the team)": "",
                        "Notes": "",
                    }
                    all_records.append(record)
                except Exception as e:
                    print(f"⚠️ Failed to parse a conflict in {file.name}: {e}")

    # Save to DataFrame
    df = pd.DataFrame(all_records)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"✅ Valid conflict resolution records exported to {output_path}")
