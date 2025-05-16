#!/usr/bin/env python3
"""
Test script to verify the UserStoryLoader can load all user story files.
"""

import os
import sys
import json

# Add the parent directory to the path to make imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)  # Add current directory to path

# Import using relative path
from user_story_loader import UserStoryLoader

# Define constants locally since we can't import them
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = project_root
CURRENT_LLM = "gpt-4o-mini"  # Default model
USER_STORY_DIR = os.path.join(BASE_DIR, "results", CURRENT_LLM, "user_stories")

def test_user_story_loader():
    """Test that the UserStoryLoader can load all user stories without errors"""
    loader = UserStoryLoader()
    
    try:
        print(f"📂 Loading user stories from: {USER_STORY_DIR}")
        print(f"🔧 Using model: {CURRENT_LLM}")
        
        loader.load_all_user_stories()
        
        print(f"\n✅ Successfully loaded {len(loader.user_stories)} user stories!")
        
        # Print some statistics
        user_groups = {}
        personas = {}
        types = {"Functional": 0, "Non-Functional": 0, "unknown": 0}
        
        for story in loader.user_stories:
            # Count by user group
            user_groups[story.user_group] = user_groups.get(story.user_group, 0) + 1
            
            # Count by persona
            personas[story.persona] = personas.get(story.persona, 0) + 1
            
            # Count by type
            if hasattr(story, 'type') and story.type:
                if story.type in types:
                    types[story.type] += 1
                else:
                    types["unknown"] += 1
            else:
                types["unknown"] += 1
        
        print("\n📊 User Stories by User Group:")
        for group, count in user_groups.items():
            print(f"  - {group}: {count} stories")
            
        print("\n📊 User Stories by Persona:")
        for persona, count in personas.items():
            print(f"  - {persona}: {count} stories")
            
        print("\n📊 User Stories by Type:")
        for type_name, count in types.items():
            print(f"  - {type_name}: {count} stories")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False
        
    return True

if __name__ == "__main__":
    success = test_user_story_loader()
    sys.exit(0 if success else 1)
