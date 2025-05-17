import os
import json

from pipeline.user_story.user_story_loader import UserStoryLoader
from pipeline.utils import (
    USER_STORY_DIR,
    load_system_summary,
    load_user_story_guidelines,
    get_llm_response,
    load_non_functional_user_story_cluster_summary
)


def build_prompt_to_cluster_non_functional_user_story(story, system_summary, guidelines):
    pillar = story.pillar
    clusters = load_non_functional_user_story_cluster_summary(pillar)
    if not clusters:
        print(f"⚠️ No cluster summary for pillar: {pillar}")
        return None
    
    cluster_defs_text = "\n".join(
        f"- {c['name']}: {c['description']}" for c in clusters
    )
    
    cluster_names = [c['name'] for c in clusters]
    cluster_names_str = ", ".join(cluster_names)

    prompt = f"""
You are a system requirements engineer.

Below is the system Summary:
{system_summary}

Below is the given system's User Story Guidelines (Definitions, Structure, and Unreal Examples):
{guidelines}

Now here is a REAL Non-Functional User Story:
ID: {story.id}
Title: {story.title}
Summary: {story.summary}
User Group: {story.user_group}
Pillar: {pillar}

Here are the cluster definitions for the pillar:
{cluster_defs_text}

Which cluster BEST fits this user story? Note that the cluster name should be one of the following: {cluster_names_str}.
Respond only with the exact **name** of the BEST cluster. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""
    return get_llm_response(prompt).strip()


def update_user_story_cluster_by_persona(story_id: str, persona_id: str, new_cluster: str):
    """Update the user story in the persona-specific file (User_stories_for_P-XXX.json)."""
    filename = f"User_stories_for_{persona_id}.json"
    filepath = os.path.join(USER_STORY_DIR, filename)

    if not os.path.exists(filepath):
        print(f"❌ File not found for persona {persona_id}: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        stories = json.load(f)

    updated = False
    for story in stories:
        if story.get("id") == story_id:
            story["cluster"] = new_cluster
            updated = True
            break

    if updated:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(stories, f, indent=2, ensure_ascii=False)
        print(f"✅ Cluster updated for {story_id} (persona {persona_id}) → {new_cluster}")
    else:
        print(f"⚠️ Story {story_id} not found in file for persona {persona_id}")
        
def cluster_non_functional_user_stories(user_story_loader: UserStoryLoader = None):
    """Main callable from main.py to cluster all non-functional user stories."""
    print("🔄 Loading user stories for clustering...")
    loader = user_story_loader if user_story_loader else UserStoryLoader()
    loader.load_all_user_stories()

    non_functional_stories = loader.filter_by_type("Non-Functional")

    # Skipping Logic: all non-functional stories already clustered
    if all(story.cluster and story.cluster.strip() for story in non_functional_stories):
        print(f"⏭️ Skipping clustering: All {len(non_functional_stories)} non-functional user stories already have a cluster.")
        return

    system_summary = load_system_summary()
    story_guidelines = load_user_story_guidelines()

    for story in non_functional_stories:
        if story.cluster and story.cluster.strip():
            print(f"   ⏭️ Already clustered: {story.id} → {story.cluster}")
            continue

        print(f"🔍 Clustering {story.id} ({story.title})")
        cluster_name = build_prompt_to_cluster_non_functional_user_story(story, system_summary, story_guidelines)
        if cluster_name:
            update_user_story_cluster_by_persona(story.id, story.persona, cluster_name)
        else:
            print(f"⚠️ Skipped {story.id} – no cluster assigned")
