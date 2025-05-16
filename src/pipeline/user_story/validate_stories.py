#!/usr/bin/env python3
"""
Simplified test script to verify all JSON files can be loaded properly.
"""

import os
import sys
import json


def validate_json_files():
    """Validate that all JSON files in the user stories directories are valid"""
    # Define directory paths
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    models = ["gpt-4o-mini", "gpt-4.1-mini"]
    
    for model in models:
        user_story_dir = os.path.join(project_root, "results", model, "user_stories")
        if not os.path.exists(user_story_dir):
            print(f"Directory not found: {user_story_dir}")
            continue
        
        print(f"\n📁 Checking user stories for model: {model}")
        json_files = [f for f in os.listdir(user_story_dir) if f.endswith('.json')]
        
        if not json_files:
            print(f"No JSON files found in {user_story_dir}")
            continue
        
        print(f"Found {len(json_files)} JSON files")
        
        for filename in json_files:
            file_path = os.path.join(user_story_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    user_stories = json.load(f)
                    
                print(f"✓ {filename}: Valid JSON with {len(user_stories)} user stories")
                
                # Check structure of first story as a sample
                if user_stories:
                    first_story = user_stories[0]
                    required_fields = ['id', 'title', 'persona', 'user_group', 'task', 'use_case', 
                                      'priority', 'summary', 'type']
                    
                    # Check for missing fields
                    missing_fields = [field for field in required_fields if field not in first_story]
                    if missing_fields:
                        print(f"  ⚠️ Warning: Missing fields in first story: {', '.join(missing_fields)}")
                
            except json.JSONDecodeError as e:
                print(f"✗ {filename}: Invalid JSON - {str(e)}")
                return False
            except Exception as e:
                print(f"✗ {filename}: Error - {str(e)}")
                return False
    
    print("\n✅ All JSON files are valid!")
    return True


if __name__ == "__main__":
    success = validate_json_files()
    sys.exit(0 if success else 1)
