import json
import os

class UserPersona:
    """Class representing a single user persona."""
    
    def __init__(self, data):
        self.name = data.get("Name", "Unknown")
        self.age = data.get("Age", None)
        self.location = data.get("Location", "Unknown")
        self.occupation = data.get("Occupation", "Unknown")
        self.marital_status = data.get("Marital_Status", "Unknown")
        self.education = data.get("Education", "Unknown")
        self.technology_comfort_level = data.get("Technology_Comfort_Level", "Unknown")
        self.goals = data.get("Goals", [])
        self.challenges = data.get("Challenges", [])
        self.frustrations = data.get("Frustrations", [])
        self.preferred_device_technology = data.get("Preferred_Device_Technology", [])
        self.key_features_desired = data.get("Key_Features_Desired", [])

    def __repr__(self):
        return f"UserPersona(Name={self.name}, Age={self.age}, Occupation={self.occupation})"
    
    def display(self):
        """Prints the details of this user persona."""
        print(f"\n📌 Persona: {self.name}")
        print(f"   - Age: {self.age}")
        print(f"   - Location: {self.location}")
        print(f"   - Occupation: {self.occupation}")
        print(f"   - Marital Status: {self.marital_status}")
        print(f"   - Education: {self.education}")
        print(f"   - Technology Comfort Level: {self.technology_comfort_level}")
        print(f"   - Goals: {', '.join(self.goals) if self.goals else 'None'}")
        print(f"   - Challenges: {', '.join(self.challenges) if self.challenges else 'None'}")
        print(f"   - Frustrations: {', '.join(self.frustrations) if self.frustrations else 'None'}")
        print(f"   - Preferred Device Technology: {', '.join(self.preferred_device_technology) if self.preferred_device_technology else 'None'}")
        print(f"   - Key Features Desired: {', '.join(self.key_features_desired) if self.key_features_desired else 'None'}")


class UserPersonaLoader:
    """Class to load and store multiple user personas from JSON files."""
    
    def __init__(self, directory):
        """
        Initializes the loader with a directory path containing user persona JSON files.
        
        :param directory: str - Path to the directory with JSON persona files.
        """
        self.directory = directory
        self.personas = []

    def load(self):
        """Loads all JSON files in the specified directory into the class instance."""
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
        """Returns the list of loaded personas."""
        return self.personas

    def print_persona(self, name):
        """Prints a specific persona's details by name."""
        for persona in self.personas:
            if persona.name.lower() == name.lower():
                persona.display()
                return
        print(f"❌ Persona with name '{name}' not found.")

    def print_all_personas(self):
        """Prints details of all loaded personas."""
        if not self.personas:
            print("❌ No personas loaded.")
            return
        for persona in self.personas:
            persona.display()
        
        print()
