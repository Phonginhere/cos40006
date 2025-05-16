#!/usr/bin/env python3
"""
Script to repair all user story JSON files in one go.
Run this if your UserStoryLoader is encountering JSON parsing errors.
"""

import os
import sys
import json
import traceback
from typing import List, Dict, Any, Optional

# Define directory paths directly to avoid import issues
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The model is set in utils.py, but we need to determine it for this standalone script
# Check both common model directories
LLM_OPTIONS = ["gpt-4o-mini", "gpt-4.1-mini"]
USER_STORY_DIRS = []

for model in LLM_OPTIONS:
    user_story_dir = os.path.join(BASE_DIR, "results", model, "user_stories")
    if os.path.exists(user_story_dir):
        USER_STORY_DIRS.append((model, user_story_dir))

if not USER_STORY_DIRS:
    print("Error: Could not find user story directories in any model results folder.")
    sys.exit(1)

print(f"Found {len(USER_STORY_DIRS)} user story directories:")


def repair_json_file(file_path: str) -> bool:
    """
    Attempt to repair a JSON file with common syntax issues.
    
    Returns:
        bool: True if repaired successfully, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse as is
        try:
            data = json.loads(content)
            print(f"✓ {os.path.basename(file_path)} is already valid")
            return True
        except json.JSONDecodeError as e:
            print(f"× Error in {os.path.basename(file_path)}: {e}")
            
            # Create a backup
            backup_path = file_path + ".bak"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Common repairs:
            
            # 1. Fix missing commas between list items
            if "Expecting ',' delimiter" in str(e):
                lines = content.splitlines()
                line_index = e.lineno - 1
                col_index = e.colno - 1
                
                # Insert comma at the position
                if 0 <= line_index < len(lines):
                    line = lines[line_index]
                    if 0 <= col_index < len(line):
                        fixed_line = line[:col_index] + ',' + line[col_index:]
                        lines[line_index] = fixed_line
                        fixed_content = '\n'.join(lines)
                        
                        # Test if the fix works
                        try:
                            json.loads(fixed_content)
                            # Save the fixed content
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(fixed_content)
                            print(f"✓ Fixed {os.path.basename(file_path)} by adding comma")
                            return True
                        except json.JSONDecodeError:
                            pass
            
            # 2. More aggressive repair: clean and pretty-print the valid parts
            # This is a last resort when specific fixes fail
            try:
                # Try to manually find and fix the problem when possible
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Print the problematic area
                error_line = e.lineno - 1
                start = max(0, error_line - 3)
                end = min(len(lines), error_line + 3)
                
                print("\nProblematic section:")
                for i in range(start, end):
                    marker = "→" if i == error_line else " "
                    print(f"{marker} {i+1}: {lines[i].rstrip()}")
                
                # Ask for manual intervention
                print("\nFailed to automatically fix. You may need to:")
                print("1. Check for missing commas between objects")
                print("2. Check for unclosed quotes or brackets")
                print("3. Look for trailing commas at the end of lists")
                print(f"\nEdit the file manually: {file_path}")
                
                return False
                
            except Exception as e:
                print(f"Failed to repair: {str(e)}")
                return False
                
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        traceback.print_exc()
        return False


def repair_all_user_story_files():
    """Attempt to repair all user story JSON files in the directory"""
    
    if not os.path.exists(USER_STORY_DIR):
        print(f"Error: User story directory not found at {USER_STORY_DIR}")
        return
    
    json_files = [f for f in os.listdir(USER_STORY_DIR) if f.endswith('.json')]
    
    if not json_files:
        print(f"No JSON files found in {USER_STORY_DIR}")
        return
    
    print(f"Found {len(json_files)} JSON files to check")
    
    repaired = 0
    failed = 0
    
    for filename in json_files:
        file_path = os.path.join(USER_STORY_DIR, filename)
        if repair_json_file(file_path):
            repaired += 1
        else:
            failed += 1
    
    print(f"\n📊 Summary: {repaired} files repaired, {failed} files need manual intervention")
    
    if failed > 0:
        print("\nFor files that couldn't be automatically repaired, you can try:")
        print("1. Check for missing commas between JSON objects")
        print("2. Verify all quotes and brackets are properly closed")
        print("3. Use a JSON validator tool online")
        print("\nRunning this command on each problematic file may help identify the issue:")
        print("python -m json.tool <filename>")


if __name__ == "__main__":
    repair_all_user_story_files()
