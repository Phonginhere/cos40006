import os
import json
import re

from collections import defaultdict
from itertools import combinations
from typing import Optional

from pipeline.user_story.user_story_loader import UserStoryLoader
from pipeline.utils import (
    USER_GROUP_KEYS,
    USER_GROUPS,
    FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH,
    FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
    load_system_summary,
    load_user_story_summary,
    get_llm_response,
    CURRENT_LLM
)


def identify_functional_conflicts_within_one_group(user_story_loader: Optional[UserStoryLoader] = None):
    os.makedirs(FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, exist_ok=True)

    # Skip if all user group files already exist
    existing_files = set(f for f in os.listdir(FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR) if f.endswith(".json"))
    if len(existing_files) >= len(USER_GROUPS):
        print("✅ Skipping functional user story conflict identification — all group JSONs already exist.")
        return

    loader = user_story_loader if user_story_loader else UserStoryLoader()
    loader.load_all_user_stories()
    functional_stories = loader.filter_by_type("Functional")

    if not functional_stories:
        print("⚠️ No functional user stories found for conflict identification.")
        return

    # Group functional stories by cluster (handle None, null, 'unclustered')
    cluster_map = defaultdict(list)
    for story in functional_stories:
        cluster = story.cluster
        if not cluster or not cluster.strip() or cluster.lower() == "unclustered":
            cluster = "(Unclustered)"
        cluster_map[cluster].append(story)

    system_summary = load_system_summary()
    user_story_guidelines = load_user_story_summary()
    conflict_technique_summary = load_functional_conflict_summary()

    conflict_id_counter = 1
    all_conflicts_by_group = {USER_GROUP_KEYS[g]: [] for g in USER_GROUPS}

    # For each cluster, process conflicts by user group
    for cluster, stories_in_cluster in cluster_map.items():
        # Group stories by user group within this cluster
        group_map = defaultdict(list)
        for story in stories_in_cluster:
            group_map[story.user_group].append(story)

        for user_group, group_stories in group_map.items():
            # Defensive check for user group validity
            if user_group not in USER_GROUP_KEYS:
                print(f"⚠️ Unknown user group '{user_group}' in cluster '{cluster}', skipping.")
                continue

            # Group stories by persona within this user group
            persona_map = defaultdict(list)
            for s in group_stories:
                persona_map[s.persona].append(s)

            persona_ids = list(persona_map.keys())

            if len(persona_ids) < 2:
                # Only one or zero personas — no conflict pairs possible
                continue

            if len(persona_ids) > 2:
                print(f"⚠️ More than 2 personas ({len(persona_ids)}) found in group '{user_group}' cluster '{cluster}'. Only handling first two.")
                # Optional: handle all pairs, but per your instructions, only assume two
                persona_ids = persona_ids[:2]

            personaA = persona_ids[0]
            personaB = persona_ids[1]

            storiesA = persona_map[personaA]
            storiesB = persona_map[personaB]

            # Nested loop compare all user stories from personaA to personaB
            for storyA in storiesA:
                for storyB in storiesB:
                    prompt = build_conflict_prompt(
                        conflict_technique_summary,
                        system_summary,
                        user_story_guidelines,
                        storyA,
                        storyB,
                        cluster,
                        user_group
                    )
                    response = get_llm_response(prompt)
                    parsed = parse_conflict_response(
                        response, conflict_id_counter, storyA, storyB, cluster, user_group
                    )
                    if parsed:
                        all_conflicts_by_group[USER_GROUP_KEYS[user_group]].append(parsed)
                        conflict_id_counter += 1

    # Save conflicts per user group
    for group_key, conflicts in all_conflicts_by_group.items():
        path = os.path.join(FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, f"{group_key}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(conflicts, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(conflicts)} conflicts for user group {group_key} at {path}")


def load_functional_conflict_summary() -> str:
    try:
        with open(FUNCTIONAL_USER_STORY_CONFLICT_SUMMARY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"❌ Could not load functional conflict summary: {e}")
        return ""


def build_conflict_prompt(
    conflict_summary: str,
    system_summary: str,
    user_story_guidelines: str,
    storyA,
    storyB,
    cluster: str,
    user_group: str,
) -> str:
    return f"""
You are an expert in functional user story conflict analysis. Apply the Chentouf technique described below:

{conflict_summary}

====================
System Context:
====================
{system_summary}

====================
User Story Guidelines:
====================
{user_story_guidelines}

====================
Compare the following TWO FUNCTIONAL user stories belonging to different personas but within the same user group and cluster:
Cluster: {cluster}
User Group: {user_group}

User Story A:
- Persona: {storyA.persona}
- Title: {storyA.title}
- Summary: {storyA.summary}

User Story B:
- Persona: {storyB.persona}
- Title: {storyB.title}
- Summary: {storyB.summary}

TASK:
If you think there is a conflict between these two user stories, identify it according to the Chentouf conflict types (Start-Forbid, Forbid-stop, Two Condition Events, Two Operation Frequencies Conflict). If there is no conflict, respond with an empty JSON object: {{}}

Only respond with a valid JSON object with the following structure:

{{
  "conflictType": "Start-Forbid" or "Forbid-stop" or "Two Condition Events" or "Two Operation Frequencies Conflict",
  "conflictDescription": "A short (1–3 sentence) description of why this is a conflict and/or why this conflict type was determined."
}}

Strictly, do not include commentary or extra text outside the JSON. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""


def parse_conflict_response(raw: str, conflict_id_counter: int, storyA, storyB, cluster: str, user_group: str) -> Optional[dict]:
    try:
        # Strip possible markdown/code blocks
        raw = re.sub(r"```(json)?", "", raw).strip()
        parsed = json.loads(raw)

        # If empty JSON or missing keys -> no conflict
        if not parsed or not parsed.get("conflictType") or not parsed.get("conflictDescription"):
            print(f"ℹ️ No conflict found between {storyA.id} and {storyB.id}")
            return None

        parsed["conflictId"] = f"FCWI-{conflict_id_counter:03d}"
        parsed["personaAId"] = storyA.persona
        parsed["personaBId"] = storyB.persona
        parsed["userGroup"] = user_group
        parsed["userStoryAId"] = storyA.id
        parsed["userStoryBId"] = storyB.id
        parsed["userStoryASummary"] = storyA.summary
        parsed["userStoryBSummary"] = storyB.summary
        parsed["cluster"] = cluster

        print(f"✅ Found conflict {parsed['conflictId']} between {storyA.id} and {storyB.id}")
        return parsed
    except Exception as e:
        print(f"❌ Failed to parse conflict response: {e}")
        print(f"Raw response: {raw[:300]}")
        return None
