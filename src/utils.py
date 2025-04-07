import json
import os

from typing import List

# Get the directory where the utils.py script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load ALFRED summary from file
def load_alfred_summary(path="data/alfred_summary.txt") -> str:
    # Convert relative path to absolute path based on script location
    abs_path = os.path.join(SCRIPT_DIR, path)
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing ALFRED summary file: {abs_path}")
    
# Load valid use case tags
def load_use_case_tags(path="data/use_case_tags.json") -> List[str]:
    # Convert relative path to absolute path based on script location
    abs_path = os.path.join(SCRIPT_DIR, path)
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            tag_data = json.load(f)
            return tag_data.get("UseCaseTags", [])
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing use case tag list: {abs_path}")

# Load requirement tags from file
def load_requirement_tags(path="data/requirement_tags.json") -> List[str]:
    # Convert relative path to absolute path based on script location
    abs_path = os.path.join(SCRIPT_DIR, path)
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            tags = json.load(f)
            return tags.get("Functional", []) + tags.get("NonFunctional", [])
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing requirement tags file: {abs_path}")