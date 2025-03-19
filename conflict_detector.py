import csv
import re
from llm_handler import get_gpt_4o_mini_response

class ConflictDetector:
    """
    Detects conflicts in system requirements by analyzing each attribute across multiple personas.
    """

    def __init__(self, system_requirements_list):
        """
        Initializes ConflictDetector with a list of SystemRequirementsSummary instances.

        :param system_requirements_list: List of SystemRequirementsSummary objects.
        """
        self.system_requirements_list = system_requirements_list
        self.conflicts = []
        self.requirement_categories = [
            "Authentication & Security", "User Management", "Data Handling", "Performance & Speed",
            "Communication & Notifications", "Payment & Transactions", "Integration & APIs",
            "Accessibility & Usability", "Analytics & Reporting", "Automation & AI",
            "Customization", "Device Compatibility", "Scalability & Performance",
            "Security & Compliance", "Reliability & Fault Tolerance", "Maintainability & Upgrades",
            "Usability & UX", "Energy Efficiency & Sustainability"
        ]

    def detect_conflicts(self):
        """
        Analyzes conflicts for each requirement category across all personas.
        """
        print("\n🔍 Detecting conflicts in system requirements...")

        for category in self.requirement_categories:
            print(f"\n🔍 Checking conflicts in: {category}")

            # Prepare structured input for LLM
            category_data = {
                req.persona.name: getattr(req, self.attribute_key(category))
                for req in self.system_requirements_list if getattr(req, self.attribute_key(category)) is not None
            }

            if not category_data:  # Skip if no data available
                continue

            # Call LLM to analyze conflicts for this category
            extracted_conflicts = self.analyze_conflicts_with_llm(category, category_data)

            # Store results if conflicts were found
            if extracted_conflicts:
                self.conflicts.append(extracted_conflicts)

        # Save conflicts if any were detected
        if self.conflicts:
            self.save_conflicts_to_csv("system_conflicts.csv")
            print("✅ Conflicts saved to system_conflicts.csv")
        else:
            print("✅ No major conflicts detected!")

        return self.conflicts

    def analyze_conflicts_with_llm(self, category, category_data):
        """
        Uses GPT-4o-mini to analyze conflicts in a specific system requirement category.
        Ignores personas that have not provided any description for the attribute.
        """
        # Filter out empty descriptions
        filtered_category_data = {name: req for name, req in category_data.items() if req.strip()}

        # If only one or zero personas provide data, there's no possible conflict
        if len(filtered_category_data) <= 1:
            return None  # No meaningful conflict analysis needed

        persona_count = len(filtered_category_data)

        # Structure input values clearly
        persona_details = "\n".join([f"- {name}'s requirement: {requirement}" for name, requirement in filtered_category_data.items()])

        prompt = f"""
        The following are the '{category}' system requirements for {persona_count} user personas:

        {persona_details}

        Analyze these requirements and identify any conflicts.
        Ignore personas that have not provided any description for this attribute.
        If conflicts exist, summarize the conflicting statements and describe why they are conflicting.
        Format the output as follows:

        Requirement Attribute: {category}
        Conflicting Statements:
        - <Persona 1>: <Statement> 
        - <Persona 2>: <Statement> 
        - <Persona 3>: <Statement> 
        Conflict Summary: <Brief explanation of why the conflict exists>
        Affected Personas: <List of persona names>

        If there are no conflicts, return "No conflict found."
        """

        response = get_gpt_4o_mini_response(prompt)

        if response and response.lower() != "no conflict found":
            return self.parse_conflict_output(response, category)

        return None

    def parse_conflict_output(self, response, category):
        """
        Parses the structured LLM response for conflicts.
        """
        conflict_pattern = re.compile(
            rf"Requirement Attribute: {category}\s*"
            r"Conflicting Statements:\s*(.*?)\s*"
            r"Conflict Summary: (.*?)\s*"
            r"Affected Personas: (.*?)\s*(?=Requirement Attribute:|$)",
            re.DOTALL
        )

        match = conflict_pattern.search(response)

        if not match:
            return None

        statements_block, conflict_summary, affected_personas = match.groups()

        # Extract individual conflicting statements
        statement_pattern = re.compile(r"- (.*?): (.*?)\n")
        conflicting_statements = statement_pattern.findall(statements_block)

        return {
            "Requirement Attribute": category,
            "Conflicting Statements": conflicting_statements,
            "Conflict Summary": conflict_summary.strip(),
            "Affected Personas": [p.strip() for p in affected_personas.split(",")]
        }

    def save_conflicts_to_csv(self, filename="system_conflicts.csv"):
        """
        Saves detected conflicts into a CSV file.
        """
        if not self.conflicts:
            print("✅ No conflicts detected. No CSV file generated.")
            return

        headers = ["Requirement Attribute", "Conflicting Statements", "Conflict Summary", "Affected Personas"]

        try:
            with open(filename, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()

                for conflict in self.conflicts:
                    writer.writerow({
                        "Requirement Attribute": conflict["Requirement Attribute"],
                        "Conflicting Statements": "\n".join([f"{p}: {s}" for p, s in conflict["Conflicting Statements"]]),
                        "Conflict Summary": conflict["Conflict Summary"],
                        "Affected Personas": ", ".join(conflict["Affected Personas"])
                    })
            
            print(f"✅ Conflicts saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving conflicts to CSV: {e}")

    def attribute_key(self, category):
        """
        Maps a category name to the corresponding attribute in the SystemRequirementsSummary class.
        """
        mapping = {
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
        return mapping.get(category, None)
