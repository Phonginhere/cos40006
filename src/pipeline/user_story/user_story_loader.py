import os
import json

from typing import List, Optional

from pipeline.utils import USER_STORY_DIR


class UserStory:
    def __init__(self, id: str, title: str, persona: str, user_group: str, task: str, use_case: str,
                 priority: int, summary: str, type: str, cluster: Optional[str] = None,
                 pillar: Optional[str] = None):
        self.id = id
        self.title = title
        self.persona = persona
        self.user_group = user_group
        self.task = task 
        self.use_case = use_case
        self.priority = priority
        self.summary = summary
        self.pillar = pillar
        self.type = type  # "Functional" or "Non-functional"
        self.cluster = cluster


    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "persona": self.persona,
            "user_group": self.user_group,
            "task": self.task,
            "use_case": self.use_case,
            "priority": self.priority,
            "summary": self.summary,
            "pillar": self.pillar,
            "type": self.type,
            "cluster": self.cluster,
        }

    @staticmethod
    def from_dict(data: dict):
        return UserStory(
            id=data["id"],
            title=data["title"],
            persona=data["persona"],
            user_group=data["user_group"],
            task=data["task"],
            use_case=data["use_case"],
            priority=data["priority"],
            summary=data["summary"],
            pillar=data.get("pillar"),
            type=data["type"],
            cluster=data.get("cluster")
        )


class UserStoryLoader:
    def __init__(self):
        self.user_stories: List[UserStory] = []

    def load_from_file(self, file_path: str):
        """
        Load user stories from a JSON file with error handling.
        
        Args:
            file_path: Path to the JSON file to load
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            self.user_stories.extend([UserStory.from_dict(d) for d in raw_data])
            print(f"✅ Loaded {len(raw_data)} stories from {os.path.basename(file_path)}")
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON Error in file: {os.path.basename(file_path)}")
            print(f"   Error details: {str(e)}")
            
            # Get the problematic line(s)
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            error_line = e.lineno - 1  # Convert to 0-based index
            start_line = max(0, error_line - 2)
            end_line = min(len(lines), error_line + 3)
            
            print("\n   Context around the error:")
            for i in range(start_line, end_line):
                line_marker = "→ " if i == error_line else "  "
                print(f"   {line_marker}{i+1}: {lines[i].rstrip()}")
            
            print("\nRun the JSON fixer script to repair this file:")
            print(f"python src/pipeline/user_story/fix_json.py")
            
            raise
        except Exception as e:
            print(f"\n❌ Error loading {os.path.basename(file_path)}: {str(e)}")
            raise

    def check_json_file(self, file_path: str, try_fix: bool = False):
        """
        Check a JSON file for syntax errors and optionally try to fix common issues.
        
        Args:
            file_path: Path to the JSON file to check
            try_fix: If True, attempt to fix simple JSON syntax errors
            
        Returns:
            tuple: (is_valid, error_message, fixed_content)
        """
        content = ""
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try parsing the JSON
            json.loads(content)
            return True, "File is valid JSON", None
        
        except json.JSONDecodeError as e:
            error_msg = f"JSON error at line {e.lineno}, column {e.colno}: {e.msg}"
            
            if not try_fix:
                return False, error_msg, None
                
            # Try to fix the error
            lines = content.splitlines(True)  # Keep line endings
            fixed_content = content
            
            # Fix for missing comma between objects in an array
            if "Expecting ',' delimiter" in str(e):
                try:
                    line_idx = e.lineno - 1
                    col_idx = e.colno - 1
                    
                    # Insert a comma at the position
                    if 0 <= line_idx < len(lines):
                        line = lines[line_idx]
                        if 0 <= col_idx < len(line):
                            fixed_line = line[:col_idx] + ',' + line[col_idx:]
                            lines[line_idx] = fixed_line
                            fixed_content = ''.join(lines)
                            
                            # Validate the fix
                            try:
                                json.loads(fixed_content)
                                return False, error_msg, fixed_content
                            except json.JSONDecodeError:
                                pass  # Fix didn't work
                except Exception:
                    pass  # Any other error during fix attempt
            
            # Add other common fixes as needed
            
            return False, error_msg, None
            
        except Exception as e:
            return False, f"Error reading file: {str(e)}", None

    def load_all_user_stories(self):
        """
        Load all user stories from JSON files in the user story directory.
        Will attempt to continue loading other files if one file has an error.
        """
        self.user_stories.clear()
        errors = []
        
        for fname in os.listdir(USER_STORY_DIR):
            if fname.endswith(".json"):
                file_path = os.path.join(USER_STORY_DIR, fname)
                try:
                    self.load_from_file(file_path)
                except Exception as e:
                    errors.append((file_path, str(e)))
        
        if errors:
            print(f"\n⚠️ Completed with {len(errors)} errors:")
            for file_path, error in errors:
                print(f"  - {os.path.basename(file_path)}: {error}")
                
            # If there are errors, let the caller decide what to do
            raise ValueError(f"{len(errors)} files could not be loaded. Run fix_json.py to repair them.")

    def save_to_file(self, file_path: str):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([story.to_dict() for story in self.user_stories], f, indent=2)

    def save_all_user_stories_by_persona(self):
        from collections import defaultdict
        grouped = defaultdict(list)
        for s in self.user_stories:
            grouped[s.persona].append(s)

        for persona_id, stories in grouped.items():
            file_path = os.path.join(USER_STORY_DIR, f"User_stories_for_{persona_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([s.to_dict() for s in stories], f, indent=2)

    def filter_by_type(self, story_type: str) -> List[UserStory]:
        return [story for story in self.user_stories if story.type.lower() == story_type.lower()]
    
    def print_clusters_for_non_functional_stories(self):
        from collections import defaultdict

        # Group non-functional stories by cluster
        cluster_map = defaultdict(list)
        for story in self.filter_by_type("Non-Functional"):
            key = story.cluster if story.cluster else "(Unclustered)"
            cluster_map[key].append(story)

        # Print the results
        print("\n📦 Non-Functional User Stories by Cluster:")
        for cluster, stories in sorted(cluster_map.items()):
            print(f"\n🔹 Cluster: {cluster} ({len(stories)} stories)")
            for s in stories:
                print(f"  • {s.id} - {s.title} [{s.persona}]")

    def print_clusters_for_functional_stories(self):
        from collections import defaultdict

        # Group functional stories by cluster
        cluster_map = defaultdict(list)
        for story in self.filter_by_type("Functional"):
            key = story.cluster if story.cluster else "(Unclustered)"
            cluster_map[key].append(story)

        # Print the results
        print("\n📦 Functional User Stories by Cluster:")
        for cluster, stories in sorted(cluster_map.items()):
            print(f"\n🔹 Cluster: {cluster} ({len(stories)} stories)")
            for s in stories:
                print(f"  • {s.id} - {s.title} [{s.persona}]")

    def get_by_persona(self, persona_id: str) -> List[UserStory]:
        return [story for story in self.user_stories if story.persona == persona_id]

    def get_by_use_case(self, use_case_id: str) -> List[UserStory]:
        return [story for story in self.user_stories if story.use_case == use_case_id]

    def get_by_priority(self, max_priority: int) -> List[UserStory]:
        return [story for story in self.user_stories if story.priority is not None and story.priority <= max_priority]

    def add_user_story(self, user_story: UserStory):
        self.user_stories.append(user_story)

    def get_all(self) -> List[UserStory]:
        return self.user_stories
