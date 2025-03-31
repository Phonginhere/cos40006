import json
import os

from typing import List

# Load ALFRED summary from file
def load_alfred_summary(path="data/alfred_summary.txt") -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing ALFRED summary file: {path}")
    
# Load valid use case tags
def load_use_case_tags(path="data/use_case_tags.json") -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            tag_data = json.load(f)
            return tag_data.get("UseCaseTags", [])
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing use case tag list: {path}")

# Load requirement tags from file
def load_requirement_tags(path="data/requirement_tags.json") -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            tags = json.load(f)
            return tags.get("Functional", []) + tags.get("NonFunctional", [])
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Missing requirement tags file: {path}")

