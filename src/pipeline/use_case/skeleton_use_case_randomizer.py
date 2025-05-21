import os
import json
import random
import hashlib
from collections import Counter, defaultdict
from typing import List, Dict
from pathlib import Path

from pipeline.use_case.use_case_loader import load_use_case_type_config
from pipeline.utils import (
    UserPersona,
    UserPersonaLoader,
    Utils,
)

# ========== Utility: Persona Group Generator ==========
def is_use_case_folder_ready(use_case_dir) -> bool:
    p = Path(use_case_dir)
    return p.exists() and any(p.glob("*.json"))

def sample_personas_by_group(pool: List[UserPersona], p_counter: Counter, pick_two_prob=0.30) -> List[UserPersona]:
    if not pool:
        return []

    # Sort by current usage (ascending), favoring underused personas
    sorted_pool = sorted(pool, key=lambda p: p_counter[p.id])
    k = 2 if random.random() < pick_two_prob and len(sorted_pool) >= 2 else 1

    return random.sample(sorted_pool[:max(2, len(sorted_pool)//2)], k=k)

def balanced_sample_use_case_types(cfg: List[Dict]) -> List[str]:
    out = []
    for rule in cfg:
        out.extend([rule["useCaseType"]] * random.randint(rule["min"], rule["max"]))
    random.shuffle(out)
    return out

def cfg_hash(cfg) -> str:
    return hashlib.md5(json.dumps(cfg, sort_keys=True).encode()).hexdigest()

def power_set_sample(optional_items: List[str]) -> List[str]:
    subsets = []
    n = len(optional_items)
    for i in range(2 ** n):
        subset = [optional_items[j] for j in range(n) if (i >> j) & 1]
        subsets.append(subset)
    return random.choice(subsets)

def write_use_case_skeletons(persona_loader: UserPersonaLoader, seed: int = None) -> None:
    if seed:
        random.seed(seed)
        
    utils = Utils()

    if is_use_case_folder_ready(utils.USE_CASE_DIR):
        print("✅ Skeletons already exist – skipping generation.")
        return

    cfg = load_use_case_type_config()
    cfg_digest = cfg_hash(cfg)

    global_cfg = next((x for x in cfg if "maxPersonaFrequencyGapRate" in x), {})
    max_gap_rate = global_cfg.get("maxPersonaFrequencyGapRate", 0.10)
    cfg = [x for x in cfg if "useCaseType" in x]  # filter only real type entries

    personas = [p for p in persona_loader.get_personas()]
    by_group = defaultdict(list)
    for p in personas:
        by_group[p.user_group].append(p)

    uc_types = balanced_sample_use_case_types(cfg)
    use_cases: list[dict] = []
    p_counter: Counter = Counter()

    for idx, uc_type in enumerate(uc_types, 1):
        rule = next(c for c in cfg if c["useCaseType"] == uc_type)

        # user groups = required + optional (power set sample)
        u_groups = set(rule["requiredUserGroups"] + power_set_sample(rule.get("optionalUserGroups", [])))

        # pillars = required + optional (power set sample)
        pillars = set(rule["requiredPillars"] + power_set_sample(rule.get("optionalPillars", [])))

        # personas
        chosen = []
        for g in u_groups:
            chosen.extend(sample_personas_by_group(by_group[g], p_counter, pick_two_prob=rule.get("pickTwoPersonasRate", 0.3)))

        p_counter.update(p.id for p in chosen)

        use_cases.append({
            "id": f"UC-{idx:03}",
            "useCaseType": uc_type,
            "userGroups": sorted(u_groups),
            "pillars": sorted(pillars),
            "personas": [p.id for p in chosen],
        })

    tot = sum(p_counter.values()) or 1
    max_allowed = max(1, int(max_gap_rate * tot))

    def gap() -> int:
        return max(p_counter.values()) - min(p_counter.values())

    while gap() > max_allowed:
        over = max(p_counter, key=p_counter.get)
        under = min(p_counter, key=p_counter.get)
        if over == under:
            break
        over_p = next(p for p in personas if p.id == over)
        under_p = next(p for p in personas if p.id == under)

        src = next((uc for uc in use_cases if over in uc["personas"] and len(uc["personas"]) > 1), None)
        dst = next((uc for uc in use_cases if under_p.user_group in uc["userGroups"] and under not in uc["personas"]), None)
        if not src or not dst:
            break
        src["personas"].remove(over)
        dst["personas"].append(under)
        p_counter[over] -= 1
        p_counter[under] += 1

    for uc in use_cases:
        if uc["personas"]:
            continue
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
            pick = random.choice(personas)
            uc["personas"].append(pick.id)
            p_counter[pick.id] += 1

    for uc in use_cases:
        random.shuffle(uc["personas"])

    Path(utils.USE_CASE_DIR).mkdir(parents=True, exist_ok=True)
    for uc in use_cases:
        (Path(utils.USE_CASE_DIR) / f"{uc['id']}.json").write_text(json.dumps(uc, indent=2, ensure_ascii=False))

    print(f"📝 Generated {len(use_cases)} skeletons; persona frequency gap={gap()}")