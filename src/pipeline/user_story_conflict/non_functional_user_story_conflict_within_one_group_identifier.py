import os
import json
import re
from collections import defaultdict
from typing import Optional

from pipeline.user_story.user_story_loader import UserStoryLoader, UserStory
from pipeline.utils import Utils


def identify_non_functional_conflicts_within_one_group(user_story_loader: Optional[UserStoryLoader] = None):
    utils = Utils()
    os.makedirs(utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, exist_ok=True)

    user_groups = utils.get_user_groups()
    user_group_keys = utils.load_user_group_keys()

    existing_files = set(f for f in os.listdir(utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR) if f.endswith(".json"))
    if len(existing_files) >= len(user_groups):
        print("✅ Skipping conflict identification — all group JSONs already exist.")
        return

    # Load decomposed user stories
    with open(utils.NON_FUNCTIONAL_USER_STORY_DECOMPOSITION_PATH, "r", encoding="utf-8") as f:
        decomposed_data = json.load(f)
    decomposed_map = {entry["id"]: entry for entry in decomposed_data}

    loader = user_story_loader if user_story_loader else UserStoryLoader()
    loader.load_all_user_stories()
    non_functional_stories = loader.filter_by_type("Non-Functional")

    cluster_map = defaultdict(list)
    for story in non_functional_stories:
        if story.cluster:
            cluster_map[story.cluster].append(story)

    system_context = utils.load_system_context()
    user_story_guidelines = utils.load_user_story_guidelines()
    technique_summary = utils.load_non_functional_user_story_conflict_technique_description()

    conflict_id_counter = 1
    all_conflicts_by_group = {user_group_keys[g]: [] for g in user_groups}
    
    # Load LLM response language proficiency level
    proficiency_level = utils.load_llm_response_language_proficiency_level()

    for cluster, stories in cluster_map.items():
        group_map = defaultdict(list)
        for s in stories:
            group_map[s.user_group].append(s)

        for user_group, group_stories in group_map.items():
            group_key = user_group_keys.get(user_group)
            if not group_key:
                continue

            persona_map = defaultdict(list)
            for s in group_stories:
                persona_map[s.persona].append(s)

            if len(persona_map) < 2:
                continue

            persona_ids = list(persona_map.keys())
            for i in range(len(persona_ids)):
                for j in range(i + 1, len(persona_ids)):
                    pid_a = persona_ids[i]
                    pid_b = persona_ids[j]
                    stories_a = persona_map[pid_a]
                    stories_b = persona_map[pid_b]

                    for sa in stories_a:
                        for sb in stories_b:
                            if sa.id not in decomposed_map or sb.id not in decomposed_map:
                                continue
                            prompt = build_conflict_prompt(
                                technique_summary,
                                system_context,
                                utils.load_user_group_description(group_key),
                                user_story_guidelines,
                                sa,
                                sb,
                                cluster,
                                decomposed_map[sa.id]["decomposition"],
                                decomposed_map[sb.id]["decomposition"],
                                proficiency_level
                            )
                            response = utils.get_llm_response(prompt)
                            parsed = parse_conflict_response(response, conflict_id_counter, sa, sb, cluster, user_group)
                            if parsed:
                                all_conflicts_by_group[group_key].append(parsed)
                                conflict_id_counter += 1

    for group_key, conflicts in all_conflicts_by_group.items():
        if conflicts:
            path = os.path.join(utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, f"{group_key}.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(conflicts, f, indent=2, ensure_ascii=False)


def build_conflict_prompt(
    technique_summary: str,
    system_context: str,
    user_group_summary: str,
    user_story_guidelines: str,
    story_a: UserStory,
    story_b: UserStory,
    cluster: str,
    decomposition_a: list,
    decomposition_b: list,
    proficiency_level: str = "",
) -> str:
    return f"""
You are an expert in non-functional requirement analysis. You are identifying conflicts between two non-functional user stories in a software system.

--- SYSTEM CONTEXT ---
{system_context}
------------------------------

--- IDENTIFICATION TECHNIQUE ---
Apply the Sadana and Liu technique for indentifying non-functional requirement (a.k.a user story) conflicts (within one user group):
{technique_summary}
------------------------------

--- USER GROUP CONTEXT ---
{user_group_summary}
------------------------------

--- USER STORY GUIDELINES ---
{user_story_guidelines}
------------------------------

--- YOUR TASK ---
Cluster of the two user stories below: {cluster}
Compare the following two non-functional user stories. Report any conflicts between them using the Sadana and Liu's technique mentioned above, focusing on the lowest-level non-functional (decomposed) user stories.

If there is no conflict, respond with an empty JSON object: {{}}
Note that, please strictly follow the definition of conflict between two user stories in the Chentouf's technique summary. Do not consider diversity of user preferences or slight differences in user stories as a conflict.
If you think the conflict found is a mild or nuanced one, it is likely that the user stories are not conflicting at all. In that case, please respond with an empty JSON object: {{}}.

Do NOT attempt to propose resolutions. Only identify clear contradictions or incompatible goals.

User Story A (ID: {story_a.id}, Persona: {story_a.persona}):
- Title: {story_a.title}
- Summary: {story_a.summary}
- Decomposed NFRs:
{json.dumps(decomposition_a, indent=2)}

User Story B (ID: {story_b.id}, Persona: {story_b.persona}):
- Title: {story_b.title}
- Summary: {story_b.summary}
- Decomposed NFRs:
{json.dumps(decomposition_b, indent=2)}

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
------------------------------

{proficiency_level}

--- END OF PROMPT ---
""".strip()


def parse_conflict_response(raw: str, conflict_id_counter: int, sa: UserStory, sb: UserStory, cluster: str, group: str) -> Optional[dict]:
    try:
        raw = re.sub(r"```(json)?", "", raw).strip()
        parsed = json.loads(raw)

        # If no conflicts were identified, skip this pair
        if (
            not parsed.get("conflictingNfrPairs") or
            not isinstance(parsed["conflictingNfrPairs"], list) or
            len(parsed["conflictingNfrPairs"]) == 0
        ):
            print(f"ℹ️ No conflict found between {sa.id} and {sb.id}")
            return None

        if not parsed.get("conflictType") or not parsed.get("conflictDescription"):
            raise ValueError("Missing required conflict fields in LLM output")

        parsed["conflictId"] = f"NFCWI-{conflict_id_counter:03d}"
        parsed["personaAId"] = sa.persona
        parsed["personaBId"] = sb.persona
        parsed["userGroup"] = group
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
