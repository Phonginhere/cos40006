# Function to build the prompt for generating raw requirements for each pillar
def build_pillar_prompt(user_group: str, pillar_name: str, previous_requirements: list[RawRequirement]) -> str:
    """
    Builds a prompt to generate raw requirements for a specific user group and pillar,
    considering previous pillar outputs to avoid duplication and confusion.
    """
    alfred_summary = load_alfred_summary()
    group_summary = load_user_group_summary(user_group)

    prev_reqs_text = ""
    if previous_requirements:
        prev_reqs_text = "\n\nPreviously defined requirements for earlier pillars:\n" + json.dumps(
            [r.to_dict() for r in previous_requirements],
            indent=2,
            ensure_ascii=False
        )

    return f"""
You are a system analyst helping define core functional requirements for a virtual assistant platform called **ALFRED**.

--- ALFRED SYSTEM SUMMARY ---
{alfred_summary}

--- USER GROUP CONTEXT: {user_group.replace("_", " ").title()} ---
{group_summary}

Your task is to write a list of system-level functional/non-funcational requirements for the ALFRED platform, specifically for the above user group, and:

🧱 **{pillar_name}**

{prev_reqs_text}

Please generate **5 to 7** requirements in a JSON array. Each requirement should include:
- A unique **title** (A concise title summarizing the requirement)
- A short **description** (set of 1–3 sentences, which is a more detailed explanation of the requirement)
- A list of **acceptanceCriteria** (2–3 concise statements for validating the feature (can be broad, high-level))
- A **priority** from 1 to 5, where:
  1 = Very high priority. Will be implemented.
  2 = High priority. Important for the ALFRED system; an implementation is planned.
  3 = Normal priority. Will be implemented if resources are available.
  4 = Low priority. Only considered if synergies with other stories exist.
  5 = Out of scope. Will not be implemented.

⚠️ Use the number only. For example: `"priority": 2` — do not use words like "High", "Low", or "Medium". Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.

📤 Output format:
```json
[
  {{
    "title": "...",
    "description": "...",
    "acceptanceCriteria": ["...", "..."],
    "priority": 1
  }},
  ...
]

Example below (DO NOT rely 100% on this example. This is just to help you understand the format and level of detail expected in the output. The requirements should be based on the user group summary (Caregivers) and ALFRED system summary you’ve been provided, and they should reflect the specific needs of caregivers in relation to the ALFRED system.):

[
  {{
    "id": "REQ-001",
    "title": "Voice-Activated Commands",
    "description": "Older adults should be able to use voice commands to interact with ALFRED for basic tasks such as setting reminders, checking the weather, or calling family members.",
    "acceptanceCriteria": [
      "ALFRED should accurately interpret and respond to voice commands.",
      "Voice commands should be simple and easy to remember."
    ],
    "priority": "2"
  }},
  ...
]

Strictly, do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""