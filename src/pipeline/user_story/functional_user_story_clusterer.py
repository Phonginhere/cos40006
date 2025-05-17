import os
import json

from pipeline.user_story.user_story_loader import UserStoryLoader
from pipeline.utils import (
    load_system_summary,
    load_user_story_guidelines,
    load_functional_user_story_clustering_technique,
    get_llm_response,
    FUNCTIONAL_USER_STORY_CLUSTER_SET_PATH,
    USER_STORY_DIR
)

def build_cluster_definition_prompt(system_summary: str, story_guidelines: str, technique_text: str, non_functional_stories: list) -> str:
    joined_nf_stories = "\n".join(
        f"- [{s.id}] {s.title} ({s.pillar})\n  Summary: {s.summary}" for s in non_functional_stories
    )

    return f"""You are a system requirement engineer applying the technique by Poort and de With (2015) to classify Functional Requirements based on their relationship to Non-Functional Requirements.

In the context of the following system, you will analyze the list of Non-Functional User Stories (NFUSs), and define functional requirement clusters.

--- SYSTEM OVERVIEW ---
{system_summary}

--- USER STORY RULES & GUIDELINES ---
{story_guidelines}

--- TECHNIQUE DESCRIPTION ---
{technique_text}

--- NON-FUNCTIONAL USER STORIES (NFUSs) ---
{joined_nf_stories}

--- TASK ---
You must define a list of functional user story clusters, where each cluster is directly derived from a non-functional user story. For each cluster, include:
- `nfus_id`: ID of the non-functional user story
- `nfus_summary`: Summary of the non-functional user story
- `cluster_name`: A short, general topic name (1–4 words), summarizing the main functional concern (e.g., “Video Communication”, “Data Sharing”, “App Updates”, “Safety Monitoring”). Avoid long or overly specific phrases.
- `cluster_description`: A short description of the kind of functional user stories that should belong to this cluster

--- OUTPUT FORMAT ---
[
  {{
    "nfus_id": "US-XXX",
    "nfus_summary": "...",
    "cluster_name": "[Short general topic]",
    "cluster_description": "Functional stories related to [describe kinds of user functionalities or system operations] that must adhere to [quality or concern expressed in the NFUS]."
  }},
  ...
]

Only output a single valid JSON list as shown, with 1 entry per NFUS. No commentary, no markdown, no extraneous formatting.
""".strip()

def generate_functional_cluster_definitions():
    output_path = FUNCTIONAL_USER_STORY_CLUSTER_SET_PATH

    # Step-Skipping Logic
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list) and len(existing_data) > 0:
                    print(f"⏭️ Skipping cluster definition generation: file already exists with {len(existing_data)} cluster(s).")
                    return
        except Exception as e:
            print(f"⚠️ Failed to read existing cluster file, will regenerate: {e}")

    print("📥 Loading user stories and system documentation...")

    system_summary = load_system_summary()
    story_guidelines = load_user_story_guidelines()

    loader = UserStoryLoader()
    loader.load_all_user_stories()
    nfus_list = loader.filter_by_type("Non-Functional")

    if not nfus_list:
        print("❌ No non-functional user stories found.")
        return

    print(f"📊 Found {len(nfus_list)} non-functional user stories, which will be sent to the LLM for functional user story cluster generation...")

    technique_text = load_functional_user_story_clustering_technique()
    prompt = build_cluster_definition_prompt(system_summary, story_guidelines, technique_text, nfus_list)

    try:
        response = get_llm_response(prompt)
        cluster_data = json.loads(response)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cluster_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Functional cluster definitions saved to: {output_path}")

    except Exception as e:
        print(f"❌ Failed to generate or parse LLM output: {e}")
        
def build_prompt_to_cluster_functional_user_story(story, system_summary, guidelines, cluster_definitions):
    formatted_clusters = "\n".join(
        f"- {cluster['cluster_name']}: {cluster['cluster_description']}" for cluster in cluster_definitions
    )

    return f"""
You are a system requirements engineer.

Below is the system Summary:
{system_summary}

Below is the given system's User Story Guidelines (Definitions, Structure, and Unreal Examples):
{guidelines}

Here is a REAL Functional User Story:
ID: {story.id}
Title: {story.title}
Summary: {story.summary}
User Group: {story.user_group}
Pillar: {story.pillar}

Below are available functional user story clusters:
{formatted_clusters}

TASK:
Select the best-matching cluster name from the list above. If no suitable match exists, respond with (Unclustered).

Strictly, only respond with the exact **cluster name** (or **(Unclustered)** only). Do not include any additional text (even explanations) or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
""".strip()


def update_user_story_cluster_by_persona(story_id: str, persona_id: str, new_cluster: str):
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


def cluster_functional_user_stories(user_story_loader: UserStoryLoader = None):
    print("🔄 Loading user stories for functional clustering...")
    loader = user_story_loader if user_story_loader else UserStoryLoader()
    loader.load_all_user_stories()

    functional_stories = loader.filter_by_type("Functional")

    # Skipping Logic
    if all(story.cluster and story.cluster.strip() for story in functional_stories):
        print(f"⏭️ Skipping clustering: All {len(functional_stories)} functional user stories already have a cluster.")
        return

    # Load supporting documents
    system_summary = load_system_summary()
    guidelines = load_user_story_guidelines()

    with open(FUNCTIONAL_USER_STORY_CLUSTER_SET_PATH, "r", encoding="utf-8") as f:
        cluster_definitions = json.load(f)

    print(f"📊 {len(functional_stories)} functional stories to process...")

    for story in functional_stories:
        if story.cluster and story.cluster.strip():
            print(f"   ⏭️ Already clustered: {story.id} → {story.cluster}")
            continue

        print(f"🔍 Clustering {story.id} ({story.title})...")

        prompt = build_prompt_to_cluster_functional_user_story(
            story, system_summary, guidelines, cluster_definitions
        )

        try:
            cluster_name = get_llm_response(prompt).strip()
            if not cluster_name:
                cluster_name = "(Unclustered)"
        except Exception as e:
            print(f"❌ Failed for {story.id}: {e}")
            cluster_name = "(Unclustered)"

        update_user_story_cluster_by_persona(story.id, story.persona, cluster_name)