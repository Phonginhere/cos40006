import os
import json
import pandas as pd

from pathlib import Path
from typing import Dict
from collections import defaultdict

from pipeline.utils import Utils


def analyze_use_case_task_extraction_and_deduplication():
    utils = Utils()

    unique_dir = Path(utils.UNIQUE_EXTRACTED_USE_CASE_TASKS_DIR)
    duplicate_dir = Path(utils.DUPLICATED_UNIQUE_EXTRACTED_USE_CASE_TASKS_DIR)
    
    if not unique_dir.exists() or not duplicate_dir.exists():
        print("❌ Unique or duplicate task directories do not exist.")
        return

    output_path = utils.USE_CASE_TASK_EXTRACTION_AND_DEDUPLICATION_ANALYSIS_CSV_FILE_PATH
    if os.path.exists(output_path):
        print(f"⚠️ {output_path} already exists. Please delete it to regenerate.")
        return        

    persona_ids = set()
    persona_task_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
        "unique": 0,
        "duplicate": 0
    })

    # Load unique tasks
    for file in sorted(unique_dir.glob("Unique_extracted_tasks_for_*.json")):
        pid = file.stem.replace("Unique_extracted_tasks_for_", "")
        persona_ids.add(pid)

        try:
            tasks = json.loads(file.read_text(encoding="utf-8"))
            persona_task_stats[pid]["unique"] = len(tasks)
        except Exception as e:
            print(f"❌ Failed to load {file.name}: {e}")

    # Load duplicated tasks
    for file in sorted(duplicate_dir.glob("Duplicated_extracted_tasks_for_*.json")):
        pid = file.stem.replace("Duplicated_extracted_tasks_for_", "")
        persona_ids.add(pid)

        try:
            tasks = json.loads(file.read_text(encoding="utf-8"))
            persona_task_stats[pid]["duplicate"] = len(tasks)
        except Exception as e:
            print(f"❌ Failed to load {file.name}: {e}")

    records = []
    total_unique = 0
    total_duplicate = 0
    
    for pid in sorted(persona_ids):
        dup = persona_task_stats[pid]["duplicate"]
        uniq = persona_task_stats[pid]["unique"]
        total = dup + uniq
        percent = f"{round((uniq / total) * 100) if total > 0 else 0}%"
        
        total_unique += uniq
        total_duplicate += dup

        records.append({
            "Personas": pid,
            "Total number of tasks extracted (from use cases)": total,
            "Number of duplicated tasks": dup,
            "Number of unique tasks": uniq,
            "Percentage of Unique Task extracted": percent,
        })

    # Add total row
    total_row = {
        "Personas": "Total",
        "Total number of tasks extracted (from use cases)": total_unique + total_duplicate,
        "Number of duplicated tasks": total_duplicate,
        "Number of unique tasks": total_unique,
        "Percentage of Unique Task extracted": f"{round((total_unique / (total_unique + total_duplicate)) * 100) if (total_unique + total_duplicate) > 0 else 0}%"
    }
    records.append(total_row)

    df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"✅ Task extraction & deduplication analysis saved to {output_path}")


def analyze_task_distribution_by_use_case_and_persona():
    utils = Utils()
    input_dir = utils.UNIQUE_EXTRACTED_USE_CASE_TASKS_DIR
    output_path = utils.USE_CASE_UNIQUE_TASK_DISTRIBUTION_ANALYSIS_CSV_FILE_PATH
    
    if os.path.exists(output_path):
        print(f"⚠️ {output_path} already exists. Please delete it to regenerate.")
        return

    task_matrix = defaultdict(lambda: defaultdict(int))
    all_personas = set()
    all_use_cases = set()

    # Process each persona's unique tasks
    for filename in os.listdir(input_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(input_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            tasks = json.load(f)

        for task in tasks:
            uc_id = task["useCaseId"]
            persona_id = task["personaId"]
            task_matrix[uc_id][persona_id] += 1
            all_personas.add(persona_id)
            all_use_cases.add(uc_id)

    all_personas = sorted(all_personas)
    all_use_cases = sorted(all_use_cases)

    # Construct rows
    data_rows = []
    for uc_id in all_use_cases:
        row = {"Use Case ID": uc_id}
        row_total = 0
        for pid in all_personas:
            count = task_matrix[uc_id].get(pid, 0)
            row[pid] = count
            row_total += count
        row["Total"] = row_total
        data_rows.append(row)

    # Add total row
    total_row = {"Use Case ID": "Total"}
    grand_total = 0
    for pid in all_personas:
        total_row[pid] = sum(row.get(pid, 0) for row in data_rows)
        grand_total += total_row[pid]
    total_row["Total"] = grand_total
    data_rows.append(total_row)

    df = pd.DataFrame(data_rows)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ Use case task-per-persona matrix saved to {output_path}")