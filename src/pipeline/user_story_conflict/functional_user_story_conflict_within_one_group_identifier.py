import os
import json
import re

from collections import defaultdict
from itertools import combinations
from typing import Optional

from pipeline.user_story.user_story_loader import UserStoryLoader
from pipeline.utils import Utils

def identify_functional_conflicts_within_one_group(user_story_loader: Optional[UserStoryLoader] = None):
    utils = Utils()
    
    os.makedirs(utils.FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, exist_ok=True)

    # Skip if all user group files already exist
    existing_files = set(f for f in os.listdir(utils.FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR) if f.endswith(".json"))
    if len(existing_files) >= len(utils.get_user_groups()):
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

    system_context = utils.load_system_context()
    user_story_guidelines = utils.load_user_story_guidelines()
    conflict_technique_summary = utils.load_functional_user_story_conflict_technique_description()

    conflict_id_counter = 1
    user_group_keys = utils.load_user_group_keys()
    user_groups = utils.get_user_groups()
    all_conflicts_by_group = {user_group_keys[g]: [] for g in user_groups}
    
    # Load LLM response language proficiency level
    proficiency_level = utils.load_llm_response_language_proficiency_level()

    # For each cluster, process conflicts by user group
    for cluster, stories_in_cluster in cluster_map.items():
        # Group stories by user group within this cluster
        group_map = defaultdict(list)
        for story in stories_in_cluster:
            group_map[story.user_group].append(story)

        for user_group, group_stories in group_map.items():
            # Defensive check for user group validity
            if user_group not in user_group_keys:
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
                        system_context,
                        user_story_guidelines,
                        storyA,
                        storyB,
                        cluster,
                        user_group,
                        proficiency_level,
                    )
                    response = utils.get_llm_response(prompt)
                    parsed = parse_conflict_response(
                        response, conflict_id_counter, storyA, storyB, cluster, user_group
                    )
                    if parsed:
                        all_conflicts_by_group[user_group_keys[user_group]].append(parsed)
                        conflict_id_counter += 1

    # Save conflicts per user group
    for group_key, conflicts in all_conflicts_by_group.items():
        path = os.path.join(utils.FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, f"{group_key}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(conflicts, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(conflicts)} conflicts for user group {group_key} at {path}")


def build_conflict_prompt(
    technique_summary: str,
    system_context: str,
    user_story_guidelines: str,
    storyA,
    storyB,
    cluster: str,
    user_group: str,
    proficiency_level: str = ""
) -> str:
    return f"""
You are an expert in functional user story conflict analysis. You are identifying conflicts between two functional user stories within the same user group and cluster.

--- SYSTEM CONTEXT ---
{system_context}
-------------------------------------

--- IDENTIFICATION TECHNIQUE ---
Apply the Chentouf technique for identifying functional user story conflicts (within one user group):
{technique_summary}
-------------------------------------

--- USER STORY GUIDELINES ---
{user_story_guidelines}
-------------------------------------

--- YOUR TASK ---
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
Note that, please strictly follow the definition of conflict between two user stories in the Chentouf's technique summary. Do not consider diversity of user preferences or slight differences in user stories as a conflict.
If you think the conflict found is a mild or nuanced one, it is likely that the user stories are not conflicting at all. In that case, please respond with an empty JSON object: {{}}.

Only respond with a valid JSON object with the following structure:

{{
  "conflictType": "Start-Forbid" or "Forbid-stop" or "Two Condition Events" or "Two Operation Frequencies Conflict",
  "conflictDescription": "A short (1–3 sentence) description of why this is a conflict and/or why this conflict type was determined."
}}

Strictly, do not include commentary or extra text outside the JSON. Do NOT use any markdown, bold, italic, or special formatting in your response.
-------------------------------------

{proficiency_level}

--- END OF PROMPT ---
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
