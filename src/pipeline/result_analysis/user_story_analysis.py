import os
import json

import pandas as pd
from pathlib import Path
from collections import defaultdict

from pipeline.utils import Utils


def analyze_user_story_uniqueness_by_personas_summary():
    utils = Utils()

    unique_dir = Path(utils.UNIQUE_USER_STORY_DIR_PATH)
    duplicate_dir = Path(utils.DUPLICATED_USER_STORY_DIR_PATH)
    output_path = utils.USER_STORY_UNIQUENESS_ANALYSIS_BY_PERSONAS_CSV_FILE_PATH

    if not unique_dir.exists() or not duplicate_dir.exists():
        print("❌ Unique or duplicate user story directories do not exist.")
        return
    
    if os.path.exists(output_path):
        print(f"⚠️ Output file already exists: {output_path}")
        return

    persona_ids = set()
    persona_stats = defaultdict(lambda: {"unique": 0, "duplicate": 0})

    # Read unique user stories
    for file in unique_dir.glob("User_stories_for_*.json"):
        pid = file.stem.replace("User_stories_for_", "")
        persona_ids.add(pid)
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                persona_stats[pid]["unique"] = len(data)
        except Exception as e:
            print(f"❌ Failed to load {file.name}: {e}")

    # Read duplicated user stories
    for file in duplicate_dir.glob("Duplicated_user_stories_for_*.json"):
        pid = file.stem.replace("Duplicated_user_stories_for_", "")
        persona_ids.add(pid)
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                persona_stats[pid]["duplicate"] = len(data)
        except Exception as e:
            print(f"❌ Failed to load {file.name}: {e}")

    # Generate records
    records = []
    total_unique = 0
    total_duplicate = 0

    for pid in sorted(persona_ids):
        uniq = persona_stats[pid]["unique"]
        dup = persona_stats[pid]["duplicate"]
        total = uniq + dup
        percent = f"{round((uniq / total) * 100) if total > 0 else 0}%"

        total_unique += uniq
        total_duplicate += dup

        records.append({
            "Persona": pid,
            "Total number of User Stories (from unique tasks)": total,
            "Number of Duplicated User Stories": dup,
            "Number of Unique User Stories": uniq,
            "Percentage of Unique User Stories": percent,
        })

    # Add total row
    records.append({
        "Persona": "Total",
        "Total number of User Stories (from unique tasks)": total_unique + total_duplicate,
        "Number of Duplicated User Stories": total_duplicate,
        "Number of Unique User Stories": total_unique,
        "Percentage of Unique User Stories": f"{round((total_unique / (total_unique + total_duplicate)) * 100) if (total_unique + total_duplicate) > 0 else 0}%",
    })

    df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"✅ User story uniqueness analysis saved to {output_path}")
    
def analyze_user_story_uniqueness_by_type_summary():
    utils = Utils()

    unique_dir = Path(utils.UNIQUE_USER_STORY_DIR_PATH)
    duplicate_dir = Path(utils.DUPLICATED_USER_STORY_DIR_PATH)
    output_path = utils.USER_STORY_UNIQUENESS_ANALYSIS_BY_TYPES_CSV_FILE_PATH

    if not unique_dir.exists() or not duplicate_dir.exists():
        print("❌ Unique or duplicate user story directories do not exist.")
        return
    
    if os.path.exists(output_path):
        print(f"⚠️ Output file already exists: {output_path}")
        return

    type_stats = defaultdict(lambda: {"unique": 0, "duplicate": 0})

    # Read unique user stories
    for file in unique_dir.glob("User_stories_for_*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                stories = json.load(f)
                for story in stories:
                    story_type = story.get("type", "Unknown")
                    type_stats[story_type]["unique"] += 1
        except Exception as e:
            print(f"❌ Failed to load {file.name}: {e}")

    # Read duplicated user stories
    for file in duplicate_dir.glob("Duplicated_user_stories_for_*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                stories = json.load(f)
                for story in stories:
                    story_type = story.get("type", "Unknown")
                    type_stats[story_type]["duplicate"] += 1
        except Exception as e:
            print(f"❌ Failed to load {file.name}: {e}")

    records = []
    total_unique = 0
    total_duplicate = 0

    for story_type in sorted(type_stats.keys()):
        uniq = type_stats[story_type]["unique"]
        dup = type_stats[story_type]["duplicate"]
        total = uniq + dup
        percent = f"{round((uniq / total) * 100) if total > 0 else 0}%"

        total_unique += uniq
        total_duplicate += dup

        records.append({
            "Type": story_type,
            "Total number of User Stories": total,
            "Number of Duplicated User Stories": dup,
            "Number of Unique User Stories": uniq,
            "Percentage of Unique User Stories": percent,
        })

    # Add total row
    records.append({
        "Type": "Total",
        "Total number of User Stories": total_unique + total_duplicate,
        "Number of Duplicated User Stories": total_duplicate,
        "Number of Unique User Stories": total_unique,
        "Percentage of Unique User Stories": f"{round((total_unique / (total_unique + total_duplicate)) * 100) if (total_unique + total_duplicate) > 0 else 0}%",
    })

    df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"✅ User story uniqueness (by type) analysis saved to {output_path}")


def analyze_user_story_clustering_by_type(story_type: str = "Non-Functional"):
    from pipeline.user_story.user_story_loader import UserStoryLoader

    utils = Utils()
    output_path = (
        utils.NON_FUNCTIONAL_USER_STORY_CLUSTERING_ANALYSIS_CSV_FILE_PATH
        if story_type.lower() == "non-functional"
        else utils.FUNCTIONAL_USER_STORY_CLUSTERING_ANALYSIS_CSV_FILE_PATH
    )
    
    if os.path.exists(output_path):
        print(f"⚠️ Output file already exists: {output_path}")
        return

    loader = UserStoryLoader(utils.UNIQUE_USER_STORY_DIR_PATH)
    loader.load_all_user_stories()
    filtered_stories = loader.filter_by_type(story_type)

    # Build cluster → persona → count map
    cluster_matrix = defaultdict(lambda: defaultdict(int))
    all_personas = set()
    all_clusters = set()

    for story in filtered_stories:
        cluster = story.cluster if story.cluster else "(Unclustered)"
        persona = story.persona
        cluster_matrix[cluster][persona] += 1
        all_personas.add(persona)
        all_clusters.add(cluster)

    all_personas = sorted(all_personas)
    all_clusters = sorted(all_clusters)

    # Create data rows
    data_rows = []
    for cluster in all_clusters:
        row = {"Cluster": cluster}
        total_count = 0
        for pid in all_personas:
            count = cluster_matrix[cluster].get(pid, 0)
            row[pid] = count
            total_count += count
        row["Total"] = total_count
        data_rows.append(row)

    # Add total row
    total_row = {"Cluster": "Total"}
    for pid in all_personas:
        total_row[pid] = sum(row.get(pid, 0) for row in data_rows)
    total_row["Total"] = sum(total_row[pid] for pid in all_personas)
    data_rows.append(total_row)

    # Convert to DataFrame and save
    df = pd.DataFrame(data_rows)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"✅ {story_type} user story clustering summary saved to {output_path}")
