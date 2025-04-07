import os
import json
import csv
from typing import List
from requirement_generator import Requirement
from user_persona_loader import UserPersona

class ConflictExtractor:
    def __init__(self, requirements: List[Requirement], personas: List[UserPersona], merged_dir: str):
        self.requirements = {r.id: r for r in requirements}
        self.persona_lookup = {p.id: p.name for p in personas}
        self.merged_dir = merged_dir

    def extract_conflicts_to_csv(self, output_csv_path: str):
        rows = []

        for filename in os.listdir(self.merged_dir):
            if filename.endswith(".json"):
                tag = filename.replace(".json", "")
                filepath = os.path.join(self.merged_dir, filename)

                try:
                    with open(filepath, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        for conflict in data.get("Conflicts", []):
                            req1_id = conflict.get("Req1")
                            req2_id = conflict.get("Req2")
                            note = conflict.get("Note")
                            ctype = conflict.get("ConflictType")

                            persona1_id = req1_id[:5]
                            persona2_id = req2_id[:5]

                            persona1_name = self.persona_lookup.get(persona1_id, "Unknown")
                            persona2_name = self.persona_lookup.get(persona2_id, "Unknown")

                            req1 = self.requirements.get(req1_id)
                            req2 = self.requirements.get(req2_id)

                            req1_desc = f"{req1.id}: {req1.description}" if req1 else "N/A"
                            req2_desc = f"{req2.id}: {req2.description}" if req2 else "N/A"

                            rows.append({
                                "RequirementCluster": tag,
                                "Persona1": f"{persona1_id}: {persona1_name}",
                                "Req1": req1_desc,
                                "Persona2": f"{persona2_id}: {persona2_name}",
                                "Req2": req2_desc,
                                "ConflictType": ctype,
                                "Note": note
                            })
                except Exception as e:
                    print(f"⚠️ Failed to process {filename}: {e}")

        # Write to CSV
        with open(output_csv_path, "w", encoding="utf-8", newline="") as csvfile:
            fieldnames = [
                "RequirementCluster",
                "Persona1",
                "Req1",
                "Persona2",
                "Req2",
                "ConflictType",
                "Note"
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"✅ Conflicts exported to {output_csv_path}")
