import os
import json
import re
from collections import defaultdict
from itertools import combinations
from typing import Optional

from pipeline.user_story.user_story_loader import UserStoryLoader
from pipeline.utils import (
    USER_GROUP_KEYS,
    load_system_summary,
    load_user_story_guidelines,
    load_functional_user_story_conflict_summary,
    get_llm_response,
    FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
)


def load_json_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_conflict_prompt(
    technique_summary: str,
    system_summary: str,
    user_story_guidelines: str,
    story_a,
    story_b,
    cluster: str,
    user_group_a: str,
    user_group_b: str,
) -> str:
    return f"""
You are an expert in functional user story conflict analysis. Apply the Chentouf technique described below:

{technique_summary}

====================
System Context:
====================
{system_summary}

====================
User Story Guidelines:
====================
{user_story_guidelines}

====================
Compare the following TWO FUNCTIONAL user stories belonging to different user groups but within the same cluster:
Cluster: {cluster}
User Group A: {user_group_a}
User Group B: {user_group_b}

User Story A:
- Persona: {story_a.persona}
- Title: {story_a.title}
- Summary: {story_a.summary}

User Story B:
- Persona: {story_b.persona}
- Title: {story_b.title}
- Summary: {story_b.summary}

TASK:
If you think there is a conflict between these two user stories, identify it according to the Chentouf conflict types (Start-Forbid, Forbid-stop, Two Condition Events, Two Operation Frequencies Conflict). If there is no conflict, respond with an empty JSON object: {{}}
Note that, please strictly follow the definition of conflict between two user stories in the Chentouf's technique summary. Do not consider diversity of user preferences or slight differences in user stories as a conflict.
If you think the conflict found is a mild or nuanced one, it is likely that the user stories are not conflicting at all. In that case, please respond with an empty JSON object: {{}}.

Only respond with a valid JSON object with the following structure:

{{
  "conflictType": "Start-Forbid" or "Forbid-stop" or "Two Condition Events" or "Two Operation Frequencies Conflict",
  "conflictDescription": "A short (1–3 sentence) description of why this is a conflict and/or why this conflict type was determined."
}}

Strictly, do not include commentary or extra text outside the JSON. Do NOT use any markdown, bold, italic, or special formatting in your response.
""".strip()


def parse_conflict_response(
    raw: str,
    conflict_id_counter: int,
    story_a,
    story_b,
    cluster: str,
    user_group_a: str,
    user_group_b: str,
) -> Optional[dict]:
    try:
        raw = re.sub(r"```(json)?", "", raw).strip()
        parsed = json.loads(raw)

        # If empty JSON or missing keys -> no conflict
        if not parsed or not parsed.get("conflictType") or not parsed.get("conflictDescription"):
            print(f"ℹ️ No conflict found between {story_a.id} and {story_b.id}")
            return None

        parsed["conflictId"] = f"FCAT-{conflict_id_counter:03d}"
        parsed["personaAId"] = story_a.persona
        parsed["personaBId"] = story_b.persona
        parsed["userGroupA"] = user_group_a
        parsed["userGroupB"] = user_group_b
        parsed["userStoryAId"] = story_a.id
        parsed["userStoryBId"] = story_b.id
        parsed["userStoryASummary"] = story_a.summary
        parsed["userStoryBSummary"] = story_b.summary
        parsed["cluster"] = cluster

        print(f"✅ Found conflict {parsed['conflictId']} between {story_a.id} and {story_b.id}")

        return parsed
    except Exception as e:
        print(f"❌ Failed to parse conflict response: {e}")
        print(f"Raw response: {raw[:300]}")
        return None


def identify_functional_conflicts_across_two_groups(user_story_loader: UserStoryLoader = None):
    os.makedirs(FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR, exist_ok=True)

    loader = user_story_loader if user_story_loader else UserStoryLoader()
    loader.load_all_user_stories()
    functional_stories = loader.filter_by_type("Functional")

    if not functional_stories:
        print("⚠️ No functional user stories found for conflict identification.")
        return

    # Group functional stories by cluster
    cluster_map = defaultdict(list)
    for story in functional_stories:
        cluster = story.cluster
        if not cluster or not cluster.strip() or cluster.lower() == "unclustered":
            cluster = "(Unclustered)"
        cluster_map[cluster].append(story)

    system_summary = load_system_summary()
    user_story_guidelines = load_user_story_guidelines()
    conflict_technique_summary = load_functional_user_story_conflict_summary()

    conflict_id_counter = 1

    for cluster, stories_in_cluster in cluster_map.items():
        # Group stories by user group inside the cluster
        group_map = defaultdict(list)
        for story in stories_in_cluster:
            group_map[story.user_group].append(story)

        # Need at least two user groups to compare
        if len(group_map) < 2:
            continue

        groups_in_cluster = sorted(group_map.keys())

        # Generate all unique pairs of user groups
        for groupA, groupB in combinations(groups_in_cluster, 2):
            groupA_stories = group_map[groupA]
            groupB_stories = group_map[groupB]

            conflicts = []

            for sa in groupA_stories:
                for sb in groupB_stories:
                    prompt = build_conflict_prompt(
                        conflict_technique_summary,
                        system_summary,
                        user_story_guidelines,
                        sa,
                        sb,
                        cluster,
                        groupA,
                        groupB,
                    )
                    response = get_llm_response(prompt)
                    conflict = parse_conflict_response(
                        response,
                        conflict_id_counter,
                        sa,
                        sb,
                        cluster,
                        groupA,
                        groupB,
                    )
                    if conflict:
                        conflicts.append(conflict)
                        conflict_id_counter += 1

            if conflicts:
                filename = f"{USER_GROUP_KEYS[groupA]}_vs_{USER_GROUP_KEYS[groupB]}.json"
                path = os.path.join(FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR, filename)

                # Read existing conflicts to merge
                existing_conflicts = []
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            existing_conflicts = json.load(f)
                    except Exception as e:
                        print(f"⚠️ Failed to load existing conflict file {filename}: {e}")

                # Merge and deduplicate by sorted pair of userStory IDs
                combined_conflicts = existing_conflicts + conflicts
                unique_conflicts = []
                seen_pairs = set()
                for c in combined_conflicts:
                    pair = tuple(sorted([c["userStoryAId"], c["userStoryBId"]]))
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        unique_conflicts.append(c)

                with open(path, "w", encoding="utf-8") as f:
                    json.dump(unique_conflicts, f, indent=2, ensure_ascii=False)

                print(f"✅ Saved {len(conflicts)} new conflicts between {groupA} and {groupB} to {filename}")
