import os
import json

from typing import List, Optional

from utils import USER_STORY_DIR


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
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        self.user_stories.extend([UserStory.from_dict(d) for d in raw_data])

    def load_all_user_stories(self):
        self.user_stories.clear()
        for fname in os.listdir(USER_STORY_DIR):
            if fname.endswith(".json"):
                self.load_from_file(os.path.join(USER_STORY_DIR, fname))

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
