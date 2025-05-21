import os
import json

from collections import defaultdict
from pathlib import Path

from pipeline.utils import (
    UserPersonaLoader,
    Utils,
)


def build_batch_dedup_prompt(system_context: str, user_stories: list) -> str:
    examples = [
        {"id": story["id"], "summary": story["summary"]}
        for story in user_stories if story["summary"]
    ]

    return f"""You are a requirements engineer. You are helping with system requirement engineering for a project as follows:

--- SYSTEM CONTEXT ---
{system_context}
--------------------------------------------

--- YOUR TASK ---
Below is a list of user stories written by the same persona and related to the same feature cluster. Each user story is represented by an ID and its summary.

Your job is to identify which user stories are redundant, overly similar, or express the same intent in slightly different ways. These may include reworded duplicates, near duplicates, or stories with the same goal phrased differently.

ONLY return the list of IDs of user stories that should be removed because they are duplicates or redundant. Return this as a valid JSON array of IDs.

- List of user stories:
{json.dumps(examples, indent=2)}

📌 OUTPUT FORMAT - JSON array of IDs to remove (Below is just an example)):
[
  "US-017",
  "US-021",
  ...
]

Return ONLY the list like the above example. Do not include any explanation, commentary, or formatting. Do NOT use any markdown, bold, italic, or special formatting in your response.
--------------------------------------------

--- END OF PROMPT ---
""".strip()


def deduplicate_user_stories_for_each_persona(persona_loader: UserPersonaLoader):
    utils = Utils()
    
    # Load user personas
    all_personas = {p.id: p for p in persona_loader.get_personas()}
    
    story_dir = Path(utils.UNIQUE_USER_STORY_DIR_PATH)
    invalid_dir = Path(utils.DUPLICATED_USER_STORY_DIR_PATH)
    invalid_dir.mkdir(parents=True, exist_ok=True)
    
    # Skipping Logic
    existing_invalid_files = {
        f.name.split("Duplicated_user_stories_for_")[-1].replace(".json", "")
        for f in invalid_dir.glob("Duplicated_user_stories_for_*.json")
    }
    expected_persona_ids = set(all_personas.keys())

    if existing_invalid_files >= expected_persona_ids:
        print(f"⏭️ Skipping deduplication – all invalid user story files already exist for {len(existing_invalid_files)} personas.\n")
        return

    story_files = sorted(story_dir.glob("User_stories_for_*.json"))

    print(f"🔍 Starting cluster-based deduplication for {len(story_files)} personas...\n")

    # Load system context
    system_context = utils.load_system_context()

    for file_path in story_files:
        persona_id = file_path.stem.split("_for_")[-1]
        if persona_id not in all_personas:
            print(f"⚠️ Persona {persona_id} not found. Skipping.")
            continue

        try:
            stories = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"❌ Failed to read {file_path.name}: {e}")
            continue

        if len(stories) <= 1:
            continue

        print(f"🧠 Deduplicating {len(stories)} user stories for {persona_id}...")

        # Group stories by cluster
        cluster_map = defaultdict(list)
        for story in stories:
            cluster = story.get("cluster") or "(Unclustered)"
            cluster_map[cluster].append(story)

        to_remove_ids = []

        for cluster, cluster_stories in cluster_map.items():
            if len(cluster_stories) <= 1:
                continue

            print(f"🔎 Checking {len(cluster_stories)} stories in cluster '{cluster}'")
            prompt = build_batch_dedup_prompt(system_context, cluster_stories)
            response = utils.get_llm_response(prompt)

            try:
                result = json.loads(response)
                if isinstance(result, list):
                    to_remove_ids.extend(result)
                else:
                    print(f"⚠️ Expected a list in cluster '{cluster}', got: {type(result)}")
            except Exception as e:
                print(f"⚠️ Failed to parse LLM response for cluster '{cluster}': {e}")

        deduplicated = [s for s in stories if s["id"] not in to_remove_ids]
        duplicates = [s for s in stories if s["id"] in to_remove_ids]

        file_path.write_text(json.dumps(deduplicated, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ Removed {len(duplicates)} duplicates → {file_path.name}")

        # Save invalids to a separate file
        if duplicates:
            invalid_file = invalid_dir / f"Duplicated_user_stories_for_{persona_id}.json"
            invalid_file.write_text(json.dumps(duplicates, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"📁 Moved invalid user stories → {invalid_file.name}")

    print("🎉 Cluster-based user story deduplication complete.\n")
