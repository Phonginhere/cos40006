import os
import json
from typing import Optional

from pipeline.utils import (
    USER_GROUP_KEYS,
    USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
    load_system_summary,
    load_user_group_guidelines,
    get_llm_response,
    NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
    FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR,
    NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
    FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR,
)
from pipeline.user_persona_loader import UserPersonaLoader

def load_json_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_verification_within_one_group_prompt(
    system_summary: str,
    user_group_guidelines: str,
    userStoryASummary: str,
    userStoryBSummary: str,
) -> str:
    return f"""
You are a System Requirement Engineer. You are identifying the conflicts between two user stories belonging to a user group in the system.

====================
SYSTEM SUMMARY
====================
{system_summary}

====================
TASK
====================
You will define if there is conflict between the following user stories. Generally, two functional user stories are said to conflict if they impose directly opposing requirements on the system's behavior in the same context or condition, without allowing both to be satisfied simultaneously.

Two functional user stories contradict if their goals or constraints are clearly incompatible in a way that would be immediately obvious to an informed reader, specifically when they require different behaviors or settings in the same feature or scenario.

User story A: {userStoryASummary}
User story B: {userStoryBSummary}

Strictly respond "Yes" or "No" only. Do not include commentary or extra text. Do NOT use any markdown, bold, italic, or special formatting in your response.
""".strip()

def build_verification_across_two_group_prompt(
    system_summary: str,
    user_group_A_guidelines: str,
    user_group_B_guidelines: str,
    userStoryASummary: str,
    userStoryBSummary: str,
) -> str:
    return f"""
You are a System Requirement Engineer. You are identifying the conflicts between two user stories belonging to two different user groups in the system.

====================
SYSTEM SUMMARY
====================
{system_summary}

====================
USER GROUP A GUIDELINES
{user_group_A_guidelines}
====================

====================
USER GROUP B GUIDELINES
{user_group_B_guidelines}
====================

====================
TASK
====================
You will define if there is conflict between the following user stories. In general cases, two functional user stories contradict if their goals or constraints are clearly incompatible in a way that would be immediately obvious to an informed reader, specifically when they require different behaviors or settings in the same feature or scenario.
However, since the two following user stories belong to different user groups, you **sometimes** should be **a bit tolerant**, meaning you should consider the possibility of a conflict being acceptable if it is not a direct contradiction but rather a difference in preferences or priorities between the two groups.
On top of that, normally, if you think the contexts provided are still **completely** not relevant to each other, or **supporing/aligning** to each other, you can say that there is no conflict.

User story A: {userStoryASummary}
User story B: {userStoryBSummary}

Strictly respond "Yes" or "No" only. Do not include commentary or extra text. Do NOT use any markdown, bold, italic, or special formatting in your response.
""".strip()


def verify_conflicts(
    persona_loader: UserPersonaLoader,
    functional: bool = True,
    within_one_group: bool = True,
):
    if within_one_group:
        if functional:
            conflict_dir = FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR
        else:
            conflict_dir = NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR
    else:
        if functional:
            conflict_dir = FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR
        else:
            conflict_dir = NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR

    system_summary = load_system_summary()
    all_personas = {p.id: p for p in persona_loader.get_personas()}

    conflict_files = [f for f in os.listdir(conflict_dir) if f.endswith(".json")]

    for conflict_file in conflict_files:
        conflict_path = os.path.join(conflict_dir, conflict_file)
        try:
            conflicts = load_json_file(conflict_path)
        except Exception as e:
            print(f"❌ Failed to load conflicts file {conflict_file}: {e}")
            continue

        updated = False
        if not conflicts:
            print(f"⚠️ No conflicts in {conflict_file}, skipping")
            continue

        # Determine guidelines per conflict file
        # For across groups, the filename is like "user_group_1_vs_user_group_2.json"
        # so parse user groups from filename
        if within_one_group:
            user_group_name = conflicts[0].get("userGroup", "")
            user_group_key = USER_GROUP_KEYS.get(user_group_name)
            if not user_group_key:
                print(f"❌ Unknown user group: {user_group_name}")
                user_group_guidelines = "(Missing user group guidelines)"
            else:
                try:
                    user_group_guidelines = load_user_group_guidelines(user_group_key)
                except Exception as e:
                    print(f"⚠️ Failed to load user group guidelines for {user_group_name}: {e}")
                    user_group_guidelines = "(Missing user group guidelines)"
        else:
            # Across two groups
            try:
                # extract group keys from filename, e.g. "user_group_1_vs_user_group_3.json"
                base = conflict_file[:-5]  # remove .json
                parts = base.split("_vs_")
                if len(parts) != 2:
                    print(f"⚠️ Cannot parse user groups from filename: {conflict_file}")
                    continue
                group_key_a, group_key_b = parts
                user_group_guidelines_a = load_user_group_guidelines(group_key_a)
                user_group_guidelines_b = load_user_group_guidelines(group_key_b)
            except Exception as e:
                print(f"⚠️ Failed to load user group guidelines for groups in {conflict_file}: {e}")
                user_group_guidelines_a = "(Missing user group guidelines)"
                user_group_guidelines_b = "(Missing user group guidelines)"

        # Loop backward to safely remove invalid conflicts
        for idx in reversed(range(len(conflicts))):
            conflict = conflicts[idx]

            summaryA = conflict.get("userStoryASummary", "")
            summaryB = conflict.get("userStoryBSummary", "")

            if within_one_group:
                prompt = build_verification_within_one_group_prompt(
                    system_summary,
                    user_group_guidelines,
                    summaryA,
                    summaryB,
                )
            else:
                prompt = build_verification_across_two_group_prompt(
                    system_summary,
                    user_group_guidelines_a,
                    user_group_guidelines_b,
                    summaryA,
                    summaryB,
                )

            try:
                response = get_llm_response(prompt).strip().lower()
            except Exception as e:
                print(f"⚠️ LLM call failed for conflict {conflict.get('conflictId')}: {e}")
                continue

            if response == "yes":
                print(f"✅ Conflict {conflict.get('conflictId')} verified as valid.")
                continue
            elif response == "no":
                print(f"🗑️ Conflict {conflict.get('conflictId')} marked invalid and removed.")
                conflicts.pop(idx)
                updated = True
            else:
                print(f"⚠️ Unexpected LLM response for conflict {conflict.get('conflictId')}: '{response}'. Keeping conflict.")
                continue

        if updated:
            try:
                save_json_file(conflict_path, conflicts)
                print(f"✅ Updated conflicts saved: {conflict_file}")
            except Exception as e:
                print(f"❌ Failed to save updated conflict file {conflict_file}: {e}")
