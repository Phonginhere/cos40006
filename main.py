import os
from data_loader import UserPersonaLoader
from system_requirements_summary import SystemRequirementsSummary
from conflict_detector import ConflictDetector

def main():
    """
    Main function to load user personas, generate system requirements, and detect conflicts.
    """

    # **Step 1: Load User Personas**
    persona_directory = "personas"  # Change to the folder where JSON persona files are stored
    persona_loader = UserPersonaLoader(persona_directory)
    persona_loader.load()
    personas = persona_loader.get_personas()

    if not personas:
        print("❌ No user personas found. Please add persona JSON files.")
        return

    print(f"\n📌 Loaded {len(personas)} personas:")
    for persona in personas:
        print(f"   - {persona.name}")

    # **Step 2: Generate or Load System Requirements**
    system_requirements_list = []

    print("\n🔍 Checking system requirements for each persona...")
    for persona in personas:
        requirements = SystemRequirementsSummary(persona)
        
        # If requirements exist, they are loaded inside the SystemRequirementsSummary class
        # Otherwise, it will retrieve from LLM and save it
        system_requirements_list.append(requirements)

    print("\n✅ System requirements are now available for all personas.")

    # **Step 3: Detect Conflicts Across System Requirements**
    print("\n🔍 Running conflict detection...")
    conflict_detector = ConflictDetector(system_requirements_list)
    conflicts = conflict_detector.detect_conflicts()

    # **Step 4: Display Summary of Detected Conflicts**
    if conflicts:
        print("\n📌 Detected Conflicts:")
        for conflict in conflicts:
            print(f"\n🔴 **{conflict['Requirement Attribute']} Conflict**")
            for persona, statement in conflict["Conflicting Statements"]:
                print(f" - {persona}: {statement}")
            print(f"⚠️ Conflict Summary: {conflict['Conflict Summary']}")
            print(f"👥 Affected Personas: {', '.join(conflict['Affected Personas'])}")
    else:
        print("\n✅ No significant conflicts detected!")

    print("\n🎯 Process complete. Conflicts saved to `system_conflicts.csv`.")

if __name__ == "__main__":
    main()
