#!/usr/bin/env python3
"""
JSON File Validator and Fixer for User Stories

This script helps diagnose and fix JSON syntax errors in user story files.
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any, Tuple, Optional

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from pipeline.utils import USER_STORY_DIR


def validate_json_file(file_path: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate a JSON file and attempt to fix common syntax errors.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Tuple[bool, str, Optional[str]]: (is_valid, message, fixed_content)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the JSON
        json.loads(content)
        return True, "Valid JSON", None
    
    except json.JSONDecodeError as e:
        message = f"JSON error at line {e.lineno}, column {e.colno}: {e.msg}"
        
        # Get the problematic line(s)
        lines = content.splitlines()
        error_line_index = e.lineno - 1
        
        # Show context around the error
        start_line = max(0, error_line_index - 3)
        end_line = min(len(lines), error_line_index + 4)
        
        context = "\nContext around the error:\n"
        for i in range(start_line, end_line):
            prefix = "→ " if i == error_line_index else "  "
            line_num = str(i + 1).rjust(4)
            context += f"{prefix}{line_num}: {lines[i]}\n"
        
        message += context
        
        # Try to fix common errors
        fixed_content = None
        
        # 1. Missing comma between list items or dict entries
        if "Expecting ',' delimiter" in str(e):
            fixed_lines = lines.copy()
            col = max(0, e.colno - 1)  # Convert to 0-indexed
            fixed_line = fixed_lines[error_line_index][:col] + "," + fixed_lines[error_line_index][col:]
            fixed_lines[error_line_index] = fixed_line
            fixed_content = "\n".join(fixed_lines)
            
            # Verify the fix works
            try:
                json.loads(fixed_content)
                message += "\nAutomatically fixed by adding a missing comma."
            except json.JSONDecodeError:
                fixed_content = None
                
        # 2. Missing quote in a string
        elif "Unterminated string" in str(e):
            # This fix is more complex and would require more context analysis
            pass
        
        return False, message, fixed_content
    
    except Exception as e:
        return False, f"Error reading file: {str(e)}", None


def scan_directory(directory: str, fix: bool = False, specific_file: Optional[str] = None) -> None:
    """
    Scan a directory for JSON files and validate each one.
    
    Args:
        directory: Directory to scan
        fix: Whether to fix files with errors
        specific_file: Optional specific file to check
    """
    if specific_file:
        file_paths = [os.path.join(directory, specific_file)]
    else:
        file_paths = [
            os.path.join(directory, fname) 
            for fname in os.listdir(directory) 
            if fname.endswith('.json')
        ]
    
    total_files = len(file_paths)
    valid_files = 0
    fixed_files = 0
    error_files = []
    
    print(f"\n🔍 Checking {total_files} JSON files in {directory}\n")
    
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        is_valid, message, fixed_content = validate_json_file(file_path)
        
        if is_valid:
            print(f"✅ {file_name}: Valid JSON")
            valid_files += 1
        else:
            print(f"❌ {file_name}: Invalid JSON")
            print(message)
            
            if fixed_content and fix:
                backup_path = file_path + ".bak"
                print(f"Creating backup at {backup_path}")
                os.rename(file_path, backup_path)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                    
                print(f"✏️ Fixed and saved {file_name}")
                fixed_files += 1
            elif fixed_content:
                print("Fix available. Run with --fix to apply.")
                error_files.append(file_path)
            else:
                print("No automatic fix available. Manual correction needed.")
                error_files.append(file_path)
    
    print(f"\n📊 Summary: {valid_files} valid, {fixed_files} fixed, {len(error_files)} with errors")
    
    if error_files:
        print("\n❗ Files with errors:")
        for file_path in error_files:
            print(f"  - {os.path.basename(file_path)}")


def main():
    parser = argparse.ArgumentParser(description="Validate and fix JSON files.")
    parser.add_argument("--dir", default=USER_STORY_DIR, help="Directory containing JSON files")
    parser.add_argument("--fix", action="store_true", help="Automatically fix errors when possible")
    parser.add_argument("--file", help="Specific file to check (basename only)")
    
    args = parser.parse_args()
    
    scan_directory(args.dir, args.fix, args.file)


if __name__ == "__main__":
    main()
