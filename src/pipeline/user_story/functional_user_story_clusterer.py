import os
import json

from pipeline.user_story.user_story_loader import UserStoryLoader
from pipeline.utils import Utils

def build_cluster_definition_prompt(system_context: str, story_guidelines: str, technique_text: str, non_functional_stories: list) -> str:
    joined_nf_stories = "\n".join(
        f"- [{s.id}] {s.title} ({s.pillar})\n  Summary: {s.summary}" for s in non_functional_stories
    )

    return f"""You are a system requirement engineer applying the technique by Poort and de With (2015) to classify Functional Requirements based on their relationship to Non-Functional Requirements.

In the context of the following system, you will analyze the list of Non-Functional User Stories (NFUSs), and define functional requirement clusters.

--- SYSTEM CONTEXT ---
{system_context}
-------------------------------------

--- USER STORY GUIDELINES ---
{story_guidelines}
-------------------------------------

--- TECHNIQUE DESCRIPTION ---
{technique_text}
-------------------------------------

--- NON-FUNCTIONAL USER STORIES (NFUSs) ---
{joined_nf_stories}
-------------------------------------

--- YOUR TASK ---
You must define a list of functional user story clusters, where each cluster is directly derived from a non-functional user story. For each cluster, include:
- `nfus_id`: ID of the non-functional user story
- `nfus_summary`: Summary of the non-functional user story
- `cluster_name`: A short, general topic name (1–4 words), summarizing the main functional concern (e.g., “Video Communication”, “Data Sharing”, “App Updates”, “Safety Monitoring”). Avoid long or overly specific phrases.

--- OUTPUT FORMAT ---
[
  {{
    "nfus_id": "US-XXX",
    "nfus_summary": "...",
    "cluster_name": "[Short general topic]" # No need any description, just a short name
  }},
  ...
]

Only output a single valid JSON list as shown, with 1 entry per NFUS. No commentary, no markdown, no extraneous formatting.
-------------------------------------

--- END OF PROMPT ---
""".strip()

def generate_functional_cluster_definitions():
    utils = Utils()
    output_path = utils.FUNCTIONAL_USER_STORY_CLUSTER_SET_PATH

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

    system_context = utils.load_system_context()
    story_guidelines = utils.load_user_story_guidelines()

    loader = UserStoryLoader()
    loader.load_all_user_stories()
    nfus_list = loader.filter_by_type("Non-Functional")
    functional_stories = loader.filter_by_type("Functional")

    if not nfus_list:
        print("❌ No non-functional user stories found.")
        return

    print(f"📊 Found {len(nfus_list)} NFUS and {len(functional_stories)} FUS")

    technique_text = utils.load_functional_user_story_clustering_technique_description()
    prompt = build_cluster_definition_prompt(system_context, story_guidelines, technique_text, nfus_list)

    try:
        initial_response = utils.get_llm_response(prompt)
        initial_clusters = json.loads(initial_response)

        if not isinstance(initial_clusters, list) or not all("nfus_id" in c for c in initial_clusters):
            raise ValueError("Initial cluster response is not valid JSON list of cluster definitions")

        print(f"📦 Initial cluster count: {len(initial_clusters)}")

        # ========== RESCALING SECTION ==========
        num_fus = len(functional_stories)
        num_nfus = len(nfus_list)
        cluster_num_nfus = utils.count_all_non_functional_user_story_clusters()

        if num_nfus == 0:
            print("❌ Cannot compute adjusted cluster count: no NFUS available.")
            return

        adjusted_cluster_num = max(1, round((num_fus / num_nfus) * cluster_num_nfus))
        print(f"🔁 Rescaling functional clusters to {adjusted_cluster_num} total clusters")

        rescale_prompt = f"""
You are a system requirement engineer. You are helping to optimize the number of functional requirement clusters.

--- SYSTEM CONTEXT ---
{system_context}
------------------------------

--- USER STORY GUIDELINES ---
{story_guidelines}
------------------------------

--- TECHNIQUE DESCRIPTION ---
{technique_text}
------------------------------

--- ORIGINAL FUNCTIONAL CLUSTER DEFINITIONS (TO BE MERGED) ---
Below is the original list of functional requirement clusters. Each cluster is derived from a non-functional user story. However, we now realize this number of clusters is too large to manage efficiently:
{json.dumps(initial_clusters, indent=2)}

--- TASK ---
Please reduce and merge these clusters down to approximately {adjusted_cluster_num} merged clusters. Merge similar or overlapping topics thoughtfully.

Return only a list of cluster names in valid JSON format like:
[
  {{"cluster_name": "Cluster A"}},
  {{"cluster_name": "Cluster B"}},
  ...
]

Strictly return only a JSON array of objects with a `"cluster_name"` field each. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
------------------------------

--- END OF PROMPT ---
""".strip()

        rescale_response = utils.get_llm_response(rescale_prompt)
        reduced_clusters = json.loads(rescale_response)

        if not isinstance(reduced_clusters, list) or not all("cluster_name" in c for c in reduced_clusters):
            raise ValueError("Rescaled cluster response is not a valid JSON list of name-only cluster objects")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(reduced_clusters, f, indent=2, ensure_ascii=False)

        print(f"✅ Rescaled clusters saved to: {output_path} ({len(reduced_clusters)} clusters)")

    except Exception as e:
        print(f"❌ Failed to generate or rescale clusters: {e}")

        
def build_prompt_to_cluster_functional_user_story(story, system_context, guidelines, cluster_definitions):
    formatted_clusters = "\n".join(
        f"- {cluster.get('cluster_name') or cluster.get('name')}"
        for cluster in cluster_definitions
    )

    return f"""
You are a system requirements engineer. You are clustering functional user stories for a software system.

--- SYSTEM CONTEXT ---
{system_context}
-------------------------------------

--- USER STORY GUIDELINES ---
{guidelines}
-------------------------------------

--- FUNCTIONAL USER STORY ---
Here is a REAL Functional User Story:
ID: {story.id}
Title: {story.title}
Summary: {story.summary}
User Group: {story.user_group}
Pillar: {story.pillar}
--------------------------------------

--- LIST OF AVAILABLE FUNCTIONAL USER STORY CLUSTERS ---
Below are available functional user story clusters:
{formatted_clusters}
-------------------------------------

--- YOUR TASK ---
Select the best-matching cluster name from the list above. If no suitable match exists, respond with (Unclustered).

Strictly, only respond with the exact **cluster name** (or **(Unclustered)** only). Do not include any additional text (even explanations) or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
-------------------------------------

--- END OF PROMPT ---
""".strip()


def update_user_story_cluster_by_persona(story_id: str, persona_id: str, new_cluster: str, utils: Utils = None):
    """Update the cluster of a user story for a specific persona."""
    filename = f"User_stories_for_{persona_id}.json"
    filepath = os.path.join(utils.USER_STORY_DIR, filename)

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
    utils = Utils()
    
    print("🔄 Loading user stories for functional clustering...")
    loader = user_story_loader if user_story_loader else UserStoryLoader()
    loader.load_all_user_stories()

    functional_stories = loader.filter_by_type("Functional")

    # Skipping Logic
    if all(story.cluster and story.cluster.strip() for story in functional_stories):
        print(f"⏭️ Skipping clustering: All {len(functional_stories)} functional user stories already have a cluster.")
        return

    # Load supporting documents
    system_context = utils.load_system_context()
    guidelines = utils.load_user_story_guidelines()

    with open(utils.FUNCTIONAL_USER_STORY_CLUSTER_SET_PATH, "r", encoding="utf-8") as f:
        cluster_definitions = json.load(f)

    print(f"📊 {len(functional_stories)} functional stories to process...")

    for story in functional_stories:
        if story.cluster and story.cluster.strip():
            print(f"   ⏭️ Already clustered: {story.id} → {story.cluster}")
            continue

        print(f"🔍 Clustering {story.id} ({story.title})...")

        prompt = build_prompt_to_cluster_functional_user_story(
            story, system_context, guidelines, cluster_definitions
        )

        try:
            cluster_name = utils.get_llm_response(prompt).strip()
            if not cluster_name:
                cluster_name = "(Unclustered)"
        except Exception as e:
            print(f"❌ Failed for {story.id}: {e}")
            cluster_name = "(Unclustered)"

        update_user_story_cluster_by_persona(story.id, story.persona, cluster_name, utils)