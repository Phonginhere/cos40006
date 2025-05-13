import os
import json

from pathlib import Path

from utils import (
    load_alfred_summary,
    load_user_story_summary,
    get_llm_response,
    USER_STORY_DIR
)
from user_stories.user_story_loader import UserStory, UserStoryLoader

def build_classification_prompt(alfred_summary: str, user_story_summary: str, user_story: UserStory) -> str:
    return f"""You are a Requirement Engineer, who specializes in Identifying Functional/Non-Functional requirement(s).

The ALFRED system supports elderly, caregivers, and developers through assistive apps. Below are relevant summaries and a user story.
## ALFRED System Summary
{alfred_summary}

## ALFRED User Story Guidelines
{user_story_summary}

## Target User Story
Summary: {user_story.summary}

## Task
Please classify this user story as either "Functional" or "Non-Functional". Focus on the *summary* to guide your decision. 
Strictly, only return one of the two options. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response."""

def classify_user_story_type(story: UserStory, alfred_summary: str, user_story_summary: str) -> str:
    prompt = build_classification_prompt(alfred_summary, user_story_summary, story)
    response = get_llm_response(prompt, max_tokens=100)
    
    if response:
        response_clean = response.strip().lower()
        
        if response_clean == "non-functional":
            return "Non-Functional"
        elif response_clean == "functional":
            return "Functional"
        
    return "Unknown"

def update_user_stories_with_type():
    alfred_summary = load_alfred_summary()
    user_story_summary = load_user_story_summary()

    loader = UserStoryLoader()
    loader.load_all_user_stories()

    all_stories = loader.get_all()
    print(f"🔍 Classifying {len(all_stories)} user stories by type...")

    for story in all_stories:
        story_type = classify_user_story_type(story, alfred_summary, user_story_summary)
        story.type = story_type
        print(f"   ➤ {story.title[:40]}... → {story_type}")

    # Save updated user stories grouped by persona
    loader.save_all_user_stories_by_persona()
    print("✅ All user stories updated and saved with 'type' field.")