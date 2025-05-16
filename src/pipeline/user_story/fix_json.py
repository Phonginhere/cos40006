#!/usr/bin/env python3
"""
Script to repair all user story JSON files with syntax errors.
"""

import os
import sys
import json
import traceback

# Define directory paths directly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check both common model directories
LLM_OPTIONS = ["gpt-4o-mini", "gpt-4.1-mini"]
USER_STORY_DIRS = []

for model in LLM_OPTIONS:
    user_story_dir = os.path.join(BASE_DIR, "results", model, "user_stories")
    if os.path.exists(user_story_dir):
        USER_STORY_DIRS.append((model, user_story_dir))

if not USER_STORY_DIRS:
    print("Error: Could not find user story directories.")
    sys.exit(1)


def fix_json_file(file_path):
    """Fix common JSON syntax errors in a file"""
    print(f"Checking {os.path.basename(file_path)}...")
    
    try:
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Try parsing it as JSON first
        try:
            json.loads(content)
            print(f"  ✓ {os.path.basename(file_path)} is valid")
            return True
        except json.JSONDecodeError as e:
            print(f"  × Error: {e}")
            
            # Create a backup first
            backup_path = file_path + ".bak"
            with open(backup_path, 'w') as f:
                f.write(content)
                
            print(f"  • Created backup: {os.path.basename(backup_path)}")
            
            # Fix for the specific error we're seeing: missing commas
            if "Expecting ',' delimiter" in str(e):
                lines = content.splitlines()
                line_idx = e.lineno - 1  # Convert to 0-based
                col_idx = e.colno - 1    # Convert to 0-based
                
                if 0 <= line_idx < len(lines):
                    line = lines[line_idx]
                    if 0 <= col_idx < len(line):
                        # Insert a comma at the error position
                        fixed_line = line[:col_idx] + ',' + line[col_idx:]
                        lines[line_idx] = fixed_line
                        fixed_content = '\n'.join(lines)
                        
                        # Verify the fix works
                        try:
                            json.loads(fixed_content)
                            with open(file_path, 'w') as f:
                                f.write(fixed_content)
                            print(f"  ✓ Fixed by adding comma at line {e.lineno}, col {e.colno}")
                            return True
                        except json.JSONDecodeError as e2:
                            print(f"  × Fix attempt failed: {e2}")
            
            print(f"  ! Manual fix needed for {os.path.basename(file_path)}")
            # Show the problematic area
            lines = content.splitlines()
            error_line = e.lineno - 1
            start = max(0, error_line - 3)
            end = min(len(lines), error_line + 4)
            
            print("\n  Context around error:")
            for i in range(start, end):
                marker = "→" if i == error_line else " "
                print(f"  {marker} {i+1}: {lines[i]}")
            
            return False
    except Exception as e:
        print(f"  × Error processing file: {str(e)}")
        return False


def main():
    print(f"Found {len(USER_STORY_DIRS)} user story directories:")
    
    for model, directory in USER_STORY_DIRS:
        print(f"\n\n📂 Processing {model} user stories in {directory}")
        
        # Get all JSON files in this directory
        json_files = [
            os.path.join(directory, f) 
            for f in os.listdir(directory) 
            if f.endswith('.json')
        ]
        
        if not json_files:
            print(f"No JSON files found in {directory}")
            continue
        
        print(f"Found {len(json_files)} JSON files")
        
        # Try to fix each file
        fixed = 0
        failed = 0
        
        for file_path in json_files:
            if fix_json_file(file_path):
                fixed += 1
            else:
                failed += 1
        
        print(f"\n📊 Summary for {model}:")
        print(f"  - {fixed} files fixed")
        print(f"  - {failed} files need manual repair")
    
    print("\nFor files that couldn't be automatically fixed, try:")
    print("1. Check for missing commas between JSON objects")
    print("2. Look for unclosed quotes or brackets")
    print("3. Check for trailing commas in lists")
    print("\nUse this command to validate a JSON file:")
    print("python -m json.tool <path_to_file>")


if __name__ == "__main__":
    main()
