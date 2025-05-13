import os
import json
import random
import hashlib
import re
import textwrap

from collections import Counter, defaultdict
from typing import List, Dict   
from pathlib import Path

from user_persona_loader import UserPersonaLoader, UserPersona
from use_case_loader import load_use_case_type_config, UseCaseLoader
from utils import load_alfred_summary, load_user_group_summary, load_use_case_summary, get_llm_response, USE_CASE_DIR

# ========== Utility: Persona Group Generator ==========
def is_use_case_folder_ready() -> bool:
    """Return True iff USE_CASE_DIR exists and already contains ≥1 .json file."""
    p = Path(USE_CASE_DIR)
    return p.exists() and any(p.glob("*.json"))

def sample_personas_by_group(pool: List[UserPersona], pick_two_prob=0.30) -> List[UserPersona]:
    if not pool:
        return []
    if len(pool) == 1:
        return pool
    k = 2 if random.random() < pick_two_prob else 1
    return random.sample(pool, k=k)

def balanced_sample_use_case_types(cfg: List[Dict]) -> List[str]:
    out = []
    for rule in cfg:
        out.extend([rule["useCaseType"]] * random.randint(rule["min"], rule["max"]))
    random.shuffle(out)
    return out

def cfg_hash(cfg) -> str:
    return hashlib.md5(json.dumps(cfg, sort_keys=True).encode()).hexdigest()

def find_config_for_type(use_case_type_config, use_case_type: str) -> Dict:
    for cfg in use_case_type_config:
        if cfg['useCaseType'] == use_case_type:
            return cfg
    raise ValueError(f"No configuration found for use case type: {use_case_type}")


# ========== Step a: Write Skeleton Use Cases ==========
def generate_use_case_skeletons(persona_loader: UserPersonaLoader, seed: int = None) -> None:
    
    if seed:
        random.seed(seed)

    # fast-exit: folder already has skeletons
    if is_use_case_folder_ready():
        print("✅ Skeletons already exist – skipping generation.")
        return

    cfg = load_use_case_type_config()
    cfg_digest = cfg_hash(cfg)

    personas = persona_loader.get_personas()
    by_group = defaultdict(list)
    for p in personas:
        by_group[p.user_group].append(p)

    uc_types = balanced_sample_use_case_types(cfg)
    use_cases: list[dict] = []
    p_counter: Counter = Counter()

    for idx, uc_type in enumerate(uc_types, 1):
        rule = next(c for c in cfg if c["useCaseType"] == uc_type)

        # ---- user groups (required + ≤1 optional) ----
        u_groups = set(rule["requiredUserGroups"])
        opts = rule.get("optionalUserGroups", [])
        if opts and random.random() < 0.5:
            u_groups.add(random.choice(opts))

        # ---- pillars ----
        pillars = set(rule["requiredPillars"])
        for opt in rule.get("optionalPillars", []):
            if random.random() < 0.5:
                pillars.add(opt)

        # ---- personas ----
        chosen = []
        for g in u_groups:
            chosen.extend(sample_personas_by_group(by_group[g]))
        p_counter.update(p.id for p in chosen)

        use_cases.append({
            "id": f"UC-{idx:03}",
            "useCaseType": uc_type,
            "userGroups": sorted(u_groups),
            "pillars": sorted(pillars),
            "personas": [p.id for p in chosen],
        })

    # ---- quick balance pass (≤10 % spread) ----
    tot = sum(p_counter.values()) or 1
    max_allowed = max(1, int(0.10 * tot))

    def gap() -> int:
        return max(p_counter.values()) - min(p_counter.values())

    while gap() > max_allowed:
        over = max(p_counter, key=p_counter.get)       # most frequent pid
        under = min(p_counter, key=p_counter.get)      # least frequent pid
        if over == under:
            break

        over_p = next(p for p in personas if p.id == over)
        under_p = next(p for p in personas if p.id == under)

        # find a UC that contains `over` but has >1 persona (so we don't go empty)
        src = next(
            (uc for uc in use_cases if over in uc["personas"] and len(uc["personas"]) > 1),
            None,
        )
        if not src:
            break  # cannot safely move anything else

        # find a destination UC that can accept `under`
        dst = next(
            (
                uc
                for uc in use_cases
                if under_p.user_group in uc["userGroups"] and under not in uc["personas"]
            ),
            None,
        )
        if not dst:
            break  # nowhere to move

        # move!
        src["personas"].remove(over)
        dst["personas"].append(under)
        p_counter[over] -= 1
        p_counter[under] += 1

    # ---- ensure no UC is empty ----
    for uc in use_cases:
        if uc["personas"]:
            continue

        # pick a group already listed in the UC, sample one persona
        random.shuffle(uc["userGroups"])
        added = False
        for g in uc["userGroups"]:
            pool = [p for p in by_group[g] if p.id not in uc["personas"]]
            if pool:
                pick = random.choice(pool)
                uc["personas"].append(pick.id)
                p_counter[pick.id] += 1
                added = True
                break
        if not added:
            # fallback: just add any persona that keeps gap low
            pick = random.choice(personas)
            uc["personas"].append(pick.id)
            p_counter[pick.id] += 1

    # ---- final shuffle of persona lists ------------------------------
    for uc in use_cases:
        random.shuffle(uc["personas"]) 
        
    # ---- save ----
    Path(USE_CASE_DIR).mkdir(parents=True, exist_ok=True)
    for uc in use_cases:
        (Path(USE_CASE_DIR) / f"{uc['id']}.json").write_text(
            json.dumps(uc, indent=2, ensure_ascii=False))
        
    # meta for future checks (optional)
    # (Path(USE_CASE_DIR) / ".buildmeta.json").write_text(
    #     json.dumps({"hash": cfg_digest, "count": len(use_cases)}))

    if seed: 
        print(f"📝 Generated {len(use_cases)} skeletons (seed={seed}); "
            f"persona frequency gap={max(p_counter.values())-min(p_counter.values())}")
    else:
        print(f"📝 Generated {len(use_cases)} skeletons; "
            f"persona frequency gap={max(p_counter.values())-min(p_counter.values())}")
    

# ========== Step b: Main Entry - Generate Raw Use Cases ==========
def build_raw_use_case_prompt(
    uc,
    all_personas: dict,
    alfred_summary: str,
    uc_summary: str,
    group_summaries: dict,
    prev_names: List[str],
) -> str:

    persona_blocks, group_set = [], set()

    for pid in uc.personas:
        if persona := all_personas.get(pid):
            persona_blocks.append(f"---\n{persona.to_prompt_string()}")
            group_set.add(persona.user_group)

    persona_text = "\n".join(persona_blocks)
    group_ctx = "\n\n".join(f"{g}:\n{group_summaries[g]}" for g in sorted(group_set))
    prev_names_block = "\n".join(f"- {n}" for n in prev_names) or "None"

    return textwrap.dedent(
        f"""
You are a system requirements engineer. You are generating a suitable name and a description for a use case of ALFRED system, with "name" is LIKELY a specific subtype of the give useCaseType, otherwise it must be related to the useCaseType.

Firstly, below is the summary of a system called ALFRED:

--- ALFRED SYSTEM SUMMARY ---
{alfred_summary}

--- USER GROUP CONTEXT ---
Here are summaries of user groups involved in this use case:
{group_ctx}

--- USE-CASE DEFINITION & NOT-REAL EXAMPLES  ---
{uc_summary}
-----------------------------

Now consider the following in-progress use case (skeleton):

Use Case ID: {uc.id}
Use Case Type: {uc.use_case_type}
Use Case Pillar(s): {', '.join(uc.pillars)}
Associated User Groups: {', '.join(uc.user_groups)}
Involved Personas:
{persona_text}

Your task is to generate the following missing fields for this use case:
- "name": A concise, clear use case `"name"` (<= 6 words, Title-Case). The name must be **unique**, avoid duplicating any of the previous names, which include: {prev_names_block}
The name should align logically with above information, especially the use case type (Prefer a *more specific sub-type* of the given `use_case_type`; if that’s impossible, ensure the name is obviously related to the type).
- "description": 1–3 sentences explaining the purpose and context of the use case clearly.

Return a single valid JSON object like:
{{
  "name": "...",
  "description": "..."
}}

Strictly return only the JSON object. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.
"""
).strip()

def generate_raw_use_cases(persona_loader: UserPersonaLoader) -> None:
    os.makedirs(USE_CASE_DIR, exist_ok=True)

    alfred_summary = load_alfred_summary()
    uc_summary = load_use_case_summary()
    group_summaries = {
        "Older Adults": load_user_group_summary("older_adults"),
        "Caregivers and Medical Staff": load_user_group_summary(
            "caregivers_and_medical_staff"
        ),
        "Developers and App Creators": load_user_group_summary(
            "developers_and_app_creators"
        ),
    }

    all_personas = {p.id: p for p in persona_loader.get_personas()}
    uc_loader = UseCaseLoader()
    uc_loader.load()

    existing_names: List[str] = [
        uc.name.strip() for uc in uc_loader.get_all() if uc.name.strip()
    ]

    for uc in uc_loader.get_all():
        # decide which fields are missing
        need_name = not uc.name
        need_desc = not uc.description
        if not (need_name or need_desc):
            print(f"⏭️  {uc.id} already complete.")
            continue
        if not uc.personas:
            print(f"⚠️  {uc.id} has no personas; skipped.")
            continue

        prompt = build_raw_use_case_prompt(
            uc, all_personas, alfred_summary, uc_summary, group_summaries, existing_names
        )

        print(f"🧠  Asking model for {uc.id} ...")
        raw = get_llm_response(prompt, max_tokens=300)

        # Safety: strip code-fence or markdown accident
        raw = re.sub(r"```.*?```", "", raw, flags=re.S)

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            print(f"❌  Bad JSON for {uc.id}: {raw[:120]} ...")
            continue

        if need_name:
            uc.name = result.get("name", "").strip()
            if uc.name.lower() in (n.lower() for n in existing_names):
                uc.name += " (Alt)"
            existing_names.append(uc.name)
        if need_desc:
            uc.description = result.get("description", "").strip()

        print(f"✅  {uc.id} → “{uc.name}”")

    uc_loader.save_all()
    print("💾  Raw-name/description generation complete.")
    
    
# ========== Step c: Main Entry - Enrich Raw Use Cases with Scenarios ==========
def build_scenario_prompt(
    uc,
    all_personas: dict,
    alfred_summary: str,
    uc_summary: str,
    group_summaries: dict,
    previous_use_cases,      
) -> str:
    """Return a prompt that discourages scenario duplication."""
    # ---- current UC personas ----
    persona_blocks, group_set = [], set()

    for pid in uc.personas:
        if persona := all_personas.get(pid):
            persona_blocks.append(f"---\n{persona.to_prompt_string()}")
            group_set.add(persona.user_group)

    persona_text = "\n".join(persona_blocks)
    group_ctx = "\n\n".join(f"{g}:\n{group_summaries[g]}" for g in sorted(group_set))

    # ---- short summaries of previously-written scenarios ----
    persona_by_id = {p.id: p for p in all_personas.values()}
    prev_summaries = []
    for prev in previous_use_cases:
        if not prev.scenario or prev.id == uc.id:
            continue
        person_strs = [
            f"{persona_by_id[pid].name} ({persona_by_id[pid].role})"
            for pid in prev.personas
            if pid in persona_by_id
        ]
        actors = "; ".join(person_strs) or "Unknown personas"
        snippet = prev.scenario.replace("\n", " ").strip()[:250]
        prev_summaries.append(f"- {prev.id} – {actors}\n  {snippet}…")
    # Limit to the most recent 6 to keep tokens low
    prev_block = "\n\n".join(prev_summaries[-6:]) or "None"
    
    return textwrap.dedent(
        f"""
You are a UX storyteller.  Write a fresh, life-like, non-repetitive scenario for the provided use case of the ALFRED system.
        
--- ALFRED SUMMARY ---
{alfred_summary}
        
--- USER GROUP CONTEXT ---
Here are summaries of user groups involved in this use case:
{group_ctx}

--- USE-CASE DEFINITION & NOT-REAL EXAMPLES  ---
{uc_summary}
-----------------------------

--- THE USE CASE ---
Use Case ID: {uc.id}
Use Case Name: {uc.name}
Use Case Description: {uc.description}
Use Case Type: {uc.use_case_type}
Use Case Pillar(s): {', '.join(uc.pillars)}
Associated User Group(s): {', '.join(uc.user_groups)}
Involved Personas (actors):
{persona_text}

TASK → Compose a lifelike 200-400-word scenario that:
    • Mentions *every* persona by name or role (not by its id).  
    • Shows their motivations, interactions with ALFRED, and the outcome.  
    • Does **not** copy or closely paraphrase any previous scenario above.  

Strictly, return only the scenario narrative. Do not include any additional text or commentary. Do NOT use any markdown, bold, italic, or special formatting in your response.  
"""
    ).strip()
    
def enrich_use_cases_with_scenarios(persona_loader: UserPersonaLoader) -> None:
    """Fill the `scenario` field for each UC lacking one."""
    
    all_personas = {p.id: p for p in persona_loader.get_personas()}
    uc_summary = load_use_case_summary()
    alfred_summary = load_alfred_summary()
    group_summaries = {
        "Older Adults": load_user_group_summary("older_adults"),
        "Caregivers and Medical Staff": load_user_group_summary(
            "caregivers_and_medical_staff"
        ),
        "Developers and App Creators": load_user_group_summary(
            "developers_and_app_creators"
        ),
    }

    uc_loader = UseCaseLoader()
    uc_loader.load()

    for uc in uc_loader.get_all():
        if uc.scenario and uc.scenario.strip():
            print(f"⏭️  {uc.id} already has a scenario.")
            continue
        if not (uc.name and uc.description):
            print(f"⚠️  {uc.id} missing name/desc – generate those first.")
            continue

        prompt = build_scenario_prompt(uc, all_personas, alfred_summary, uc_summary, group_summaries, uc_loader.get_all())
        print(f"🧠  Generating scenario for {uc.id} …")
        raw = get_llm_response(prompt, max_tokens=550)

        # strip accidental markdown / code fences
        scenario = re.sub(r"```.*?```", "", raw, flags=re.S).strip()
        uc.scenario = scenario

        preview = scenario.replace("\n", " ")[:80]
        print(f"✅  {uc.id} scenario drafted → {preview}…")

    uc_loader.save_all()
    print("💾  Scenario generation complete.")