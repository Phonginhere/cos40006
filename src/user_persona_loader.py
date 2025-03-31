import json
import os

class UserPersona:
    """Represents a new-format user persona (e.g., Olivia, Elena, Thomas)."""

    def __init__(self, data):
        self.raw_data = data
        self.id = data.get("Id", "Unknown")
        self.name = data.get("Name", "Unknown")
        self.role = data.get("Role", "Unknown")
        self.tagline = data.get("Tagline", "")
        self.demographic_data = data.get("Demographic data", {})
        self.core_characteristics = data.get("Core characteristics", [])
        self.core_goals = data.get("Core goals", [])
        self.typical_challenges = data.get("Typical challenges", [])
        self.singularities = data.get("Singularities", [])
        self.working_situation = data.get("Working situation", "")
        self.place_of_work = data.get("Place of work", "")
        self.expertise = data.get("Expertise", "")
        self.main_tasks = data.get("Main tasks with system support", [])
        self.most_important_tasks = data.get("Most important tasks", [])
        self.least_important_tasks = data.get("Least important tasks", [])
        self.miscellaneous = data.get("Miscellaneous", [])

    def __repr__(self):
        return f"UserPersona(Name={self.name})"

    def display(self):
        print(f"\n👤 Persona: {self.name} (ID: {self.id})")
        print(f"   - Role: {self.role}")
        print(f"   - Tagline: {self.tagline}")
        print(f"   - Demographics: {self.demographic_data}")
        print(f"   - Core Characteristics: {', '.join(self.core_characteristics)}")
        print(f"   - Core Goals: {', '.join(self.core_goals)}")
        print(f"   - Challenges: {', '.join(self.typical_challenges)}")
        print(f"   - Singularities: {', '.join(self.singularities)}")
        print(f"   - Work Situation: {self.working_situation}")
        print(f"   - Place of Work: {self.place_of_work}")
        print(f"   - Expertise: {self.expertise}")
        print(f"   - Main Tasks: {', '.join(self.main_tasks)}")
        print(f"   - Most Important Tasks: {', '.join(self.most_important_tasks)}")
        print(f"   - Least Important Tasks: {', '.join(self.least_important_tasks)}")
        print(f"   - Miscellaneous: {', '.join(self.miscellaneous)}")


class UserPersonaLoader:
    """Loads new-format user personas from a directory of JSON files."""

    def __init__(self, directory=r"data\personas"):
        self.directory = directory
        self.personas = []

    def load(self):
        """Loads all JSON files in the directory into UserPersona instances."""
        try:
            for filename in os.listdir(self.directory):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.directory, filename)
                    with open(filepath, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        self.personas.append(UserPersona(data))
            print(f"✅ Loaded {len(self.personas)} personas successfully.")
        except Exception as e:
            print(f"❌ Error loading personas: {e}")

    def get_personas(self):
        """Returns all loaded personas."""
        return self.personas

    def print_persona(self, name):
        """Prints details of a persona by name."""
        for persona in self.personas:
            if persona.name.lower() == name.lower():
                persona.display()
                return
        print(f"❌ Persona with name '{name}' not found.")

    def print_all_personas(self):
        """Prints all loaded personas."""
        if not self.personas:
            print("❌ No personas loaded.")
            return
        for persona in self.personas:
            persona.display()
        print()
