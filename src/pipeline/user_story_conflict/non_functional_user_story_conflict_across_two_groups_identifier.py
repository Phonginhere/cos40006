import os
import json
import re
from collections import defaultdict
from itertools import combinations
from typing import Optional

from pipeline.user_story.user_story_loader import UserStoryLoader, UserStory
from pipeline.utils import (
    load_system_summary,
    load_user_group_keys,
    load_user_group_guidelines,
    load_user_story_guidelines,
    load_non_functional_user_story_conflict_summary,
    get_llm_response,
    NON_FUNCTIONAL_USER_STORY_DECOMPOSITION_PATH,
    NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
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
    user_group_guidelines_A: str,
    user_group_guidelines_B: str,
    user_story_guidelines: str,
    story_a: UserStory,
    story_b: UserStory,
    cluster: str,
    decomposition_a: list,
    decomposition_b: list,
) -> str:
    prompt = f"""
You are an expert in non-functional requirement analysis. Apply the conflict detection technique described below:

{technique_summary}

====================
System Context:
====================
{system_summary}

====================
User Group A Guidelines:
====================
{user_group_guidelines_A}

====================
User Group B Guidelines:
====================
{user_group_guidelines_B}

====================
User Story Guidelines:
====================
{user_story_guidelines}

====================
Cluster of the two user stories below: {cluster}
Compare the following two non-functional user stories. Report any conflicts between them using the Sadana and Liu's technique mentioned above, focusing on the lowest-level non-functional (decomposed) user stories.

If there is no conflict, respond with an empty JSON object: {{}}
Note that, please strictly follow the definition of conflict between two user stories in the technique summary. Do not consider diversity of user preferences or slight differences in user stories as a conflict.
If you think the conflict found is a mild or nuanced one, it is likely that the user stories are not conflicting at all. In that case, please respond with an empty JSON object: {{}}.

Do NOT attempt to propose resolutions. Only identify clear contradictions or incompatible goals.

User Story A (ID: {story_a.id}, Persona: {story_a.persona}, User Group: {story_a.user_group}):
- Title: {story_a.title}
- Summary: {story_a.summary}
- Decomposed NFRs:
{json.dumps(decomposition_a, indent=2)}

User Story B (ID: {story_b.id}, Persona: {story_b.persona}, User Group: {story_b.user_group}):
- Title: {story_b.title}
- Summary: {story_b.summary}
- Decomposed NFRs:
{json.dumps(decomposition_b, indent=2)}

====================
Format your answer strictly as a JSON object:

If conflict is found:
{{
  "conflictType": "Mutually Exclusive" or "Partial",
  "conflictDescription": "[A short (1–3 sentence) description of why this is a conflict, and/or why this conflict type is determined]",
  "conflictingNfrPairs": [
    ["<lowest-level NFR from A>", "<lowest-level NFR from B>"],
    ...
  ]
}}

If no conflict is found:
{{
  "conflictType": null,
  "conflictDescription": null,
  "conflictingNfrPairs": []
}}

Only include actual conflicting NFR pairs. Do not include commentary or extra text outside the JSON. Do NOT use any markdown, bold, italic, or special formatting in your response.
""".strip()
    return prompt


def parse_conflict_response(
    raw: str,
    conflict_id_counter: int,
    sa: UserStory,
    sb: UserStory,
    cluster: str,
    user_group_A: str,
    user_group_B: str,
) -> Optional[dict]:
    try:
        raw = re.sub(r"```(json)?", "", raw).strip()
        parsed = json.loads(raw)

        # Check for conflict presence
        if (
            not parsed.get("conflictingNfrPairs")
            or not isinstance(parsed["conflictingNfrPairs"], list)
            or len(parsed["conflictingNfrPairs"]) == 0
        ):
            print(f"ℹ️ No conflict found between {sa.id} and {sb.id}")
            return None

        if not parsed.get("conflictType") or not parsed.get("conflictDescription"):
            raise ValueError("Missing required conflict fields in LLM output")

        parsed["conflictId"] = f"NFCAT-{conflict_id_counter:03d}"
        parsed["personaAId"] = sa.persona
        parsed["personaBId"] = sb.persona
        parsed["userGroupA"] = user_group_A
        parsed["userGroupB"] = user_group_B
        parsed["userStoryAId"] = sa.id
        parsed["userStoryBId"] = sb.id
        parsed["userStoryASummary"] = sa.summary
        parsed["userStoryBSummary"] = sb.summary
        parsed["cluster"] = cluster

        print(f"✅ Found conflict {parsed['conflictId']} between {sa.id} and {sb.id}")

        return parsed

    except Exception as e:
        print(f"❌ Failed to parse conflict response: {e}")
        print(f"Raw content: {raw[:300]}")
        return None


def identify_non_functional_conflicts_across_two_groups(
    user_story_loader: UserStoryLoader = None,
):
    os.makedirs(NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR, exist_ok=True)

    loader = user_story_loader if user_story_loader else UserStoryLoader()
    loader.load_all_user_stories()
    non_functional_stories = loader.filter_by_type("Non-Functional")

    # Group stories by cluster
    cluster_map = defaultdict(list)
    for story in non_functional_stories:
        if story.cluster:
            cluster_map[story.cluster].append(story)

    # Load decomposed user stories
    with open(NON_FUNCTIONAL_USER_STORY_DECOMPOSITION_PATH, "r", encoding="utf-8") as f:
        decomposed_data = json.load(f)
    decomposed_map = {entry["id"]: entry for entry in decomposed_data}

    system_summary = load_system_summary()
    user_story_guidelines = load_user_story_guidelines()

    conflict_id_counter = 1

    for cluster, stories in cluster_map.items():
        # Group stories by user group inside the cluster
        group_map = defaultdict(list)
        for s in stories:
            group_map[s.user_group].append(s)

        # Skip clusters with less than two groups
        if len(group_map) < 2:
            continue

        groups_in_cluster = sorted(group_map.keys())
        
        user_group_keys = load_user_group_keys()

        # Generate all unique pairs of user groups
        for groupA, groupB in combinations(groups_in_cluster, 2):
            groupA_stories = group_map[groupA]
            groupB_stories = group_map[groupB]

            # Load user group summaries once per group pair
            user_group_guidelines_A = load_user_group_guidelines(user_group_keys[groupA])
            user_group_guidelines_B = load_user_group_guidelines(user_group_keys[groupB])

            conflicts = []

            for sa in groupA_stories:
                for sb in groupB_stories:
                    if sa.id not in decomposed_map or sb.id not in decomposed_map:
                        continue
                    prompt = build_conflict_prompt(
                        load_non_functional_user_story_conflict_summary(),
                        system_summary,
                        user_group_guidelines_A,
                        user_group_guidelines_B,
                        user_story_guidelines,
                        sa,
                        sb,
                        cluster,
                        decomposed_map[sa.id]["decomposition"],
                        decomposed_map[sb.id]["decomposition"],
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
                filename = f"{user_group_keys[groupA]}_vs_{user_group_keys[groupB]}.json"
                path = os.path.join(NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR, filename)

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