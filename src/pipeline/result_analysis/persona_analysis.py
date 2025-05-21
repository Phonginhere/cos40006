import os
import pandas as pd

from pipeline.utils import UserPersonaLoader, Utils

def analyze_personas(persona_loader: "UserPersonaLoader"):

    utils: Utils = Utils()

    output_path = utils.PERSONA_ANALYSIS_CSV_FILE_PATH
    if os.path.exists(output_path):
        print(f"⚠️ {output_path} already exists. Please delete it to regenerate.")
        return

    all_personas = {p.id: p for p in persona_loader.get_personas()}

    records = []

    for persona in all_personas.values():
        record = {
            "Id": persona.id,
            "Name": persona.name,
            "Role": persona.role,
            "Tagline": persona.tagline,
            "Demographics": persona.demographic_data,
            "Core Characteristics": persona.core_characteristics,
            "Core Goals": persona.core_goals,
            "Typical Challenges": persona.typical_challenges,
            "Singularities": persona.singularities,
            "Main Actions": persona.main_actions,
            "Work Situation": persona.working_situation,
            "Place of Work": persona.place_of_work,
            "Expertise": persona.expertise,
            "User Group": persona.user_group,
        }
        records.append(record)

    df = pd.DataFrame(records)

    # Ensure result directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save as CSV
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ Saved persona analysis to {output_path}")
