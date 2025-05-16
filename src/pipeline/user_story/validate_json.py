#!/usr/bin/env python3
"""
Simple test script to verify that all user story JSON files can be loaded.
"""

import os
import sys
import json

# Define paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LLM_OPTIONS = ["gpt-4o-mini", "gpt-4.1-mini"]

def validate_json_files(directory):
    """Validate that all JSON files in the directory can be parsed"""
    print(f"\nChecking JSON files in: {directory}")
    
    if not os.path.exists(directory):
        print(f"⚠️ Directory not found: {directory}")
        return 0, 0
    
    files = [f for f in os.listdir(directory) if f.endswith('.json')]
    valid = 0
    invalid = 0
    
    for filename in files:
        file_path = os.path.join(directory, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            print(f"✅ {filename}: Valid JSON")
            valid += 1
        except json.JSONDecodeError as e:
            print(f"❌ {filename}: Invalid JSON - {str(e)}")
            invalid += 1
        except Exception as e:
            print(f"❌ {filename}: Error - {str(e)}")
            invalid += 1
    
    print(f"\n📊 Summary for {os.path.basename(directory)}:")
    print(f"  - {valid} valid files")
    print(f"  - {invalid} invalid files")
    
    return valid, invalid

def main():
    """Check all user story JSON files"""
    total_valid = 0
    total_invalid = 0
    
    for model in LLM_OPTIONS:
        user_story_dir = os.path.join(PROJECT_ROOT, "results", model, "user_stories")
        valid, invalid = validate_json_files(user_story_dir)
        total_valid += valid
        total_invalid += invalid
    
    print(f"\n📊 Overall Summary:")
    print(f"  - {total_valid} valid JSON files")
    print(f"  - {total_invalid} invalid JSON files")
    
    return total_invalid == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
