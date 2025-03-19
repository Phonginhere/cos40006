import json
import os
from llm_handler import get_gpt_4o_mini_response

class SystemRequirementsSummary:
    """
    Stores system requirements for a user persona and retrieves details from LLM.
    """

    def __init__(self, persona):
        """
        Initializes a SystemRequirementsSummary instance using a UserPersona.
        
        :param persona: Instance of UserPersona containing persona details.
        """
        self.persona = persona  # Store persona instance
        self.filename = f"system_requirements_summaries/system_requirements_{self.persona.name.replace(' ', '_').lower()}.json"

        # Functional Requirements
        self.authentication_security = ""
        self.user_management = ""
        self.data_handling = ""
        self.performance_speed = ""
        self.communication_notifications = ""
        self.payment_transactions = ""
        self.integration_apis = ""
        self.accessibility_usability = ""
        self.analytics_reporting = ""
        self.automation_ai = ""
        self.customization = ""
        self.device_compatibility = ""

        # Non-Functional Requirements
        self.scalability_performance = ""
        self.security_compliance = ""
        self.reliability_fault_tolerance = ""
        self.maintainability_upgrades = ""
        self.usability_ux = ""
        self.energy_efficiency_sustainability = ""

        # Check if saved requirements exist, otherwise retrieve from LLM
        if os.path.exists(self.filename):
            print(f"📂 Loading saved system requirements for {self.persona.name} from {self.filename}")
            self.load_from_json()
        else:
            self.retrieve_llm_requirements()

    def retrieve_llm_requirements(self):
        """
        Calls LLM to fill in system requirement attributes based on the user persona.
        If a saved JSON file exists, it will load that instead.
        """
        if os.path.exists(self.filename):
            print(f"📂 Loading saved system requirements for {self.persona.name} from {self.filename}")
            self.load_from_json()
            return

        print(f"🔍 Retrieving system requirements for persona: {self.persona.name}")

        prompt = f"""
        Based on the following user persona, determine their expected system requirements in a BRIEF and CONCISE format.

        User Persona:
        {vars(self.persona)}

        Provide a structured response for each of these system requirements.
        Keep each response concise (one sentence or phrase per attribute).

        If you cannot find suitable information for a requirement attribute from the provided user persona, strictly return "None".

        Authentication & Security:
        User Management:
        Data Handling:
        Performance & Speed:
        Communication & Notifications:
        Payment & Transactions:
        Integration & APIs:
        Accessibility & Usability:
        Analytics & Reporting:
        Automation & AI:
        Customization:
        Device Compatibility:
        Scalability & Performance:
        Security & Compliance:
        Reliability & Fault Tolerance:
        Maintainability & Upgrades:
        Usability & UX:
        Energy Efficiency & Sustainability:

        Return each answer under the respective attribute heading, without any additional explanations. Also, do not make the text become bold or italic or other special formats/styles.
        """

        response = get_gpt_4o_mini_response(prompt)
        
        if response:
            self.parse_llm_response(response)
            self.save_to_json()  # Save after parsing response
        else:
            print(f"❌ Failed to retrieve system requirements for {self.persona.name}")

    def parse_llm_response(self, response):
        """
        Parses the structured LLM response and assigns values to the system requirement attributes.
        If LLM returns "None", the attribute value is set to an empty string ("").
        """
        lines = response.split("\n")
        attribute_map = {
            "Authentication & Security": "authentication_security",
            "User Management": "user_management",
            "Data Handling": "data_handling",
            "Performance & Speed": "performance_speed",
            "Communication & Notifications": "communication_notifications",
            "Payment & Transactions": "payment_transactions",
            "Integration & APIs": "integration_apis",
            "Accessibility & Usability": "accessibility_usability",
            "Analytics & Reporting": "analytics_reporting",
            "Automation & AI": "automation_ai",
            "Customization": "customization",
            "Device Compatibility": "device_compatibility",
            "Scalability & Performance": "scalability_performance",
            "Security & Compliance": "security_compliance",
            "Reliability & Fault Tolerance": "reliability_fault_tolerance",
            "Maintainability & Upgrades": "maintainability_upgrades",
            "Usability & UX": "usability_ux",
            "Energy Efficiency & Sustainability": "energy_efficiency_sustainability"
        }

        for line in lines:
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            # Ensure we correctly separate attribute name and value
            if ":" in line:
                attribute, value = line.split(":", 1)
                attribute = attribute.strip()
                value = value.strip()

                # If the attribute exists in our mapping, set the value
                if attribute in attribute_map:
                    setattr(self, attribute_map[attribute], "" if (value.lower() == "none" or value.lower() == "none.") else value)

    def to_dict(self):
        """
        Converts the system requirements into a dictionary format.
        """
        return {
            "Persona": self.persona.name,
            "Authentication & Security": self.authentication_security,
            "User Management": self.user_management,
            "Data Handling": self.data_handling,
            "Performance & Speed": self.performance_speed,
            "Communication & Notifications": self.communication_notifications,
            "Payment & Transactions": self.payment_transactions,
            "Integration & APIs": self.integration_apis,
            "Accessibility & Usability": self.accessibility_usability,
            "Analytics & Reporting": self.analytics_reporting,
            "Automation & AI": self.automation_ai,
            "Customization": self.customization,
            "Device Compatibility": self.device_compatibility,
            "Scalability & Performance": self.scalability_performance,
            "Security & Compliance": self.security_compliance,
            "Reliability & Fault Tolerance": self.reliability_fault_tolerance,
            "Maintainability & Upgrades": self.maintainability_upgrades,
            "Usability & UX": self.usability_ux,
            "Energy Efficiency & Sustainability": self.energy_efficiency_sustainability
        }

    def save_to_json(self):
        """
        Saves the system requirements into a JSON file.
        """
        os.makedirs("system_requirements", exist_ok=True)  # Ensure directory exists
        try:
            with open(self.filename, "w", encoding="utf-8") as file:
                json.dump(self.to_dict(), file, indent=4)
            print(f"✅ System requirements saved to {self.filename}")
        except Exception as e:
            print(f"❌ Error saving system requirements to JSON: {e}")

    def load_from_json(self):
        """
        Loads system requirements from a saved JSON file if available.
        It excludes loading the 'Persona' attribute.
        """
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    for key, value in data.items():
                        attribute = key.lower().replace(" ", "_")
                        if attribute != "persona" and hasattr(self, attribute):
                            setattr(self, attribute, value)
                print(f"📂 Loaded system requirements from {self.filename}")
            except Exception as e:
                print(f"❌ Error loading system requirements from JSON: {e}")
    def __str__(self):
        """
        Returns a string representation of the system requirements.
        """
        return f"System Requirements for {self.persona.name}:\n" + "\n".join(
            f"{key}: {value if value else '[No data]'}" for key, value in self.to_dict().items()
        )
