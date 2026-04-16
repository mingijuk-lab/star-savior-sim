
import sys
import os
import json

sys.path.append(os.getcwd())

import Core.calc_engine_v5 as engine

def compare_single_target():
    with open("Data/characters.json", "r", encoding="utf-8") as f:
        specs = json.load(f)
    
    from Core.data_loader_v5 import extract_json_from_md
    rotations = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    
    # Baseline substats
    substats = {"$ATK$": 0.0, "$SPD$": 0.0, "$CR$": 0.0, "$CD$": 0.0}
    engine.EQUIPMENTS = engine.setup_equipments(substats)

    # Comparisons
    # Rosaria Boss 1-target vs Lin (Standard)
    cases = [
        {"name": "로자리아", "variant": "로자리아(보스1인)", "eq": "파괴4+투지2", "blessing": "AX", "jrs": ["노페인 노게인", "누각 위, 유리달 맞이", "어느 한 기사의 맹세", "메이드 바이 페트라", "불굴의 역작"]},
        {"name": "린", "variant": "린(일반3인)", "eq": "통찰4+투지2", "blessing": "AX", "jrs": ["노페인 노게인", "누각 위, 유리달 맞이", "어느 한 기사의 맹세", "메이드 바이 페트라", "불굴의 역작"]}
    ]

    print(f"--- Single Target Comparison: Rosaria vs Lin ---")
    print("-" * 60)

    for case in cases:
        cname = case["name"]
        variant = case["variant"]
        cdata = specs[cname]
        rdata = rotations[variant]
        
        dps, total, time, _, max_h, stats = engine.calculate_dps(
            variant, cdata, rdata, case["eq"], case["jrs"], 
            blessing_name=case["blessing"], max_actions=15, force_no_ult=False
        )
        
        print(f"Character: {variant}")
        print(f"  DPS: {dps:,.2f}")
        print(f"  Max Hit: {max_h:,.0f}")
        print(f"  Speed: {stats['spd']:.0f}")
        print(f"  ATK: {stats['atk']:.0f}")
        print("-" * 30)

if __name__ == "__main__":
    compare_single_target()
