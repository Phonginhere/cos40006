import os
import json
import shutil

from collections import defaultdict

from pipeline.user_story.user_story_loader import UserStory
from pipeline.utils import (
    UserPersonaLoader,
    Utils
)


def extract_skeleton_user_stories(persona_loader: UserPersonaLoader):
    utils = Utils()
    
    # Step 1: Load persona map
    all_personas = {p.id: p for p in persona_loader.get_personas()}

    # Step 1.1: Check if story files already exist and match expected count
    if os.path.exists(utils.USER_STORY_DIR):
        existing_files = set(os.listdir(utils.USER_STORY_DIR))
        expected_files = {f"User_stories_for_{pid}.json" for pid in all_personas}
        
        if expected_files.issubset(existing_files) and len(expected_files) == len(all_personas):
            print("✅ All skeleton user story files already exist. Skipping extraction.")
            return
    
    # Step 2: Clean user story directory
    if os.path.exists(utils.USER_STORY_DIR):
        shutil.rmtree(utils.USER_STORY_DIR)
    os.makedirs(utils.USER_STORY_DIR, exist_ok=True)

    # Step 3: Process extracted task files
    grouped_stories = defaultdict(list)
    uid_counter = 1

    for filename in os.listdir(utils.EXTRACTED_USE_CASE_TASKS_DIR):
        if not filename.startswith("Extracted_tasks_for_") or not filename.endswith(".json"):
            continue

        file_path = os.path.join(utils.EXTRACTED_USE_CASE_TASKS_DIR, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                task_list = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load {filename}: {e}")
            continue

        for task_obj in task_list:
            persona_id = task_obj["personaId"]
            uc_id = task_obj["useCaseId"]
            task = task_obj["taskDescription"]

            user_group = all_personas[persona_id].user_group if persona_id in all_personas else "Unknown"

            story = UserStory(
                id=f"US-{uid_counter:03}",
                title="",
                persona=persona_id,
                user_group=user_group,
                use_case=uc_id,
                priority=None,
                summary="",
                type="",
                cluster=None,
                pillar=None,
                task=task
            )
            grouped_stories[persona_id].append(story)
            uid_counter += 1

    # Step 4: Write grouped user stories per persona
    for persona_id, stories in grouped_stories.items():
        file_path = os.path.join(utils.USER_STORY_DIR, f"User_stories_for_{persona_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([s.to_dict() for s in stories], f, indent=2, ensure_ascii=False)

    print(f"✅ Extracted and saved user stories for {len(grouped_stories)} persona(s).")
