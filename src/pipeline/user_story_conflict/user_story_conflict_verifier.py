import os
import json
from typing import Optional

from pipeline.utils import (
    UserPersonaLoader,
    Utils,
)


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

--- SYSTEM SUMMARY ---
{system_summary}
----------------------

--- USER GROUP GUIDELINES ---
{user_group_guidelines}
----------------------

--- YOUR TASK ---
You will define if there is conflict between the following user stories. Generally, two functional user stories are said to conflict if they impose directly opposing requirements on the system's behavior in the same context or condition, without allowing both to be satisfied simultaneously.
In other words, two functional user stories contradict if their goals or constraints are clearly incompatible in a way that would be immediately obvious to an informed reader, specifically when they require different behaviors or settings in the same feature or scenario.

User story 1: {userStoryASummary}
User story 2: {userStoryBSummary}

Strictly respond "Yes" or "No" only. Do not include commentary or extra text. Do NOT use any markdown, bold, italic, or special formatting in your response.
-----------------------

--- END OF PROMPT ---
""".strip()

def build_verification_across_two_group_prompt(
    system_summary: str,
    user_group_A_guidelines: str,
    user_group_B_guidelines: str,
    userStoryASummary: str,
    userStoryBSummary: str,
) -> str:
    return f"""
You are a System Requirement Engineer. You are identifying the conflicts between two user stories belonging to two different user groups in a software system.

--- SYSTEM SUMMARY ---
{system_summary}
----------------------

--- USER GROUPS GUIDELINES ---
- User Group A:
{user_group_A_guidelines}

- User Group B:
{user_group_B_guidelines}
----------------------

--- YOUR TASK ---
You will define if there is conflict between the following user stories. In general cases, two functional user stories contradict if their goals or constraints are clearly incompatible in a way that would be immediately obvious to an informed reader, specifically when they require different behaviors or settings in the same feature or scenario.

User story a (User group A): {userStoryASummary}
User story b (User group B): {userStoryBSummary}

Strictly respond "Yes" or "No" only. Do not include commentary or extra text. Do NOT use any markdown, bold, italic, or special formatting in your response.
-----------------------

--- END OF PROMPT ---
""".strip()


def verify_conflicts(
    persona_loader: UserPersonaLoader,
    functional: bool = True,
    within_one_group: bool = True,
):
    utils = Utils()

    # Conflict source directory
    if within_one_group:
        if functional:
            conflict_dir = utils.FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR
            invalid_dir = utils.INVALID_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR
        else:
            conflict_dir = utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR
            invalid_dir = utils.INVALID_NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR
    else:
        if functional:
            conflict_dir = utils.FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR
            invalid_dir = os.path.join(utils.INVALID_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR, "functional_user_stories")
        else:
            conflict_dir = utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR
            invalid_dir = os.path.join(utils.INVALID_USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR, "non_functional_user_stories")

    os.makedirs(invalid_dir, exist_ok=True)
    
    # Load system summary and personas
    system_summary = utils.load_system_summary()
    all_personas = {p.id: p for p in persona_loader.get_personas()}

    conflict_files = [f for f in os.listdir(conflict_dir) if f.endswith(".json")]

    for conflict_file in conflict_files:
        conflict_path = os.path.join(conflict_dir, conflict_file)
        try:
            conflicts = load_json_file(conflict_path)
        except Exception as e:
            print(f"❌ Failed to load conflicts file {conflict_file}: {e}")
            continue

        if not conflicts:
            print(f"⚠️ No conflicts in {conflict_file}, skipping")
            continue

        if within_one_group:
            user_group_name = conflicts[0].get("userGroup", "")
            user_group_keys = utils.load_user_group_keys()
            user_group_key = user_group_keys.get(user_group_name)
            if not user_group_key:
                print(f"❌ Unknown user group: {user_group_name}")
                user_group_guidelines = "(Missing user group guidelines)"
            else:
                try:
                    user_group_guidelines = utils.load_user_group_description(user_group_key)
                except Exception as e:
                    print(f"⚠️ Failed to load user group guidelines for {user_group_name}: {e}")
                    user_group_guidelines = "(Missing user group guidelines)"
        else:
            try:
                base = conflict_file[:-5]
                parts = base.split("_vs_")
                if len(parts) != 2:
                    print(f"⚠️ Cannot parse user groups from filename: {conflict_file}")
                    continue
                group_key_a, group_key_b = parts
                user_group_guidelines_a = utils.load_user_group_description(group_key_a)
                user_group_guidelines_b = utils.load_user_group_description(group_key_b)
            except Exception as e:
                print(f"⚠️ Failed to load user group guidelines for groups in {conflict_file}: {e}")
                user_group_guidelines_a = "(Missing)"
                user_group_guidelines_b = "(Missing)"

        updated = False
        valid_conflicts = []
        invalid_conflicts = []

        for conflict in conflicts:
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
                response = utils.get_llm_response(prompt).strip().lower()
            except Exception as e:
                print(f"⚠️ LLM call failed for conflict {conflict.get('conflictId')}: {e}")
                valid_conflicts.append(conflict)
                continue

            if response == "yes":
                print(f"✅ Conflict {conflict.get('conflictId')} verified as valid.")
                valid_conflicts.append(conflict)
            elif response == "no":
                print(f"🗑️ Conflict {conflict.get('conflictId')} marked invalid.")
                invalid_conflicts.append(conflict)
                updated = True
            else:
                print(f"⚠️ Unexpected LLM response for conflict {conflict.get('conflictId')}: '{response}'. Keeping conflict.")
                valid_conflicts.append(conflict)

        # Write valid conflicts back to original file
        if updated:
            try:
                save_json_file(conflict_path, valid_conflicts)
                print(f"✅ Updated valid conflicts: {conflict_file}")
            except Exception as e:
                print(f"❌ Failed to save updated conflict file {conflict_file}: {e}")

        # Write invalid conflicts to corresponding subfolder
        if invalid_conflicts:
            invalid_path = os.path.join(invalid_dir, conflict_file)
            try:
                save_json_file(invalid_path, invalid_conflicts)
                print(f"📁 Moved {len(invalid_conflicts)} invalid conflict(s) → {invalid_path}")
            except Exception as e:
                print(f"❌ Failed to save invalid conflicts: {invalid_path}: {e}")