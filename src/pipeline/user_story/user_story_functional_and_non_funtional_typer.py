import os
import json

from pathlib import Path

from pipeline.user_story.user_story_loader import UserStory, UserStoryLoader
from pipeline.utils import Utils


def build_classification_prompt(system_summary: str, user_story_summary: str, user_story: UserStory) -> str:
    return f"""You are a Requirement Engineer, who specializes in Identifying Functional/Non-Functional requirement(s).

Below are relevant summaries and a user story.
## System Summary
{system_summary}

## The given system's User Story Guidelines
{user_story_summary}

## Target User Story
Summary: {user_story.summary}

## Task
Please classify this user story as either "Functional" or "Non-Functional". Focus on the *summary* to guide your decision. 
Strictly, only return one of the two options. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response."""

def classify_user_story_type(story: UserStory, system_summary: str, user_story_summary: str, utils: Utils) -> str:
    prompt = build_classification_prompt(system_summary, user_story_summary, story)
    response = utils.get_llm_response(prompt)

    if response:
        response_clean = response.strip().lower()
        
        if response_clean == "non-functional":
            return "Non-Functional"
        elif response_clean == "functional":
            return "Functional"
        
    return "Unknown"

def update_user_stories_with_type():
    utils = Utils()

    system_summary = utils.load_system_context()
    user_story_summary = utils.load_user_story_guidelines()

    loader = UserStoryLoader()
    loader.load_all_user_stories()

    all_stories = loader.get_all()
    
    # Step Skipping Logic
    persona_ids = set(story.persona for story in all_stories)
    complete_personas = {
        pid for pid in persona_ids
        if all(story.type and story.type.strip() for story in loader.get_by_persona(pid))
    }

    if complete_personas == persona_ids:
        print(f"⏭️ Skipping classification: All user stories for {len(persona_ids)} personas are already typed.")
        return

    # Process only stories that are not classified
    print(f"🔍 Classifying {len(all_stories)} user stories by type...")

    for story in all_stories:
        story_type = classify_user_story_type(story, system_summary, user_story_summary, utils)
        story.type = story_type
        print(f"   ➤ {story.title[:40]}... → {story_type}")

    # Save updated user stories grouped by persona
    loader.save_all_user_stories_by_persona()
    print("✅ All user stories updated and saved with 'type' field.")