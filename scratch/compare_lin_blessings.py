
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

import Core.calc_engine_v5 as engine
from Core.models_v5 import StatType

def compare_lin():
    # Load data
    with open("Data/characters.json", "r", encoding="utf-8") as f:
        specs = json.load(f)
    
    from Core.data_loader_v5 import extract_json_from_md
    rotations = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    
    char_name = "린"
    cdata = specs[char_name]
    rdata = rotations[char_name]
    
    # Setup equipments with 0 substats for baseline
    substats = {"$ATK$": 0.0, "$SPD$": 0.0, "$CR$": 0.0, "$CD$": 0.0}
    engine.EQUIPMENTS = engine.setup_equipments(substats)
    
    # We'll use the best known journey combination for Lin from the optimization guide
    # From previous check: ['노페인 노게인', '누각 위, 유리달 맞이', '어느 한 기사의 맹세', '메이드 바이 페트라', '불굴의 역작']
    jr_names = ["노페인 노게인", "누각 위, 유리달 맞이", "어느 한 기사의 맹세", "메이드 바이 페트라", "불굴의 역작"]
    eq_name = "통찰4+투지2"
    
    print(f"--- Comparison for [{char_name}] (Standard Strategy) ---")
    print(f"Set: {eq_name}")
    print(f"Journeys: {', '.join(jr_names)}")
    print("-" * 50)

    # Comparison
    for b_name in ["AX", "FX"]:
        dps, total, time, _, max_h, stats = engine.calculate_dps(
            char_name, cdata, rdata, eq_name, jr_names, 
            blessing_name=b_name, max_actions=15, force_no_ult=False
        )
        
        print(f"Blessing: {b_name}")
        print(f"  DPS: {dps:,.2f}")
        print(f"  Total Damage: {total:,.2f}")
        print(f"  Max Hit: {max_h:,.0f}")
        print(f"  Final ATK: {stats['atk']:,.0f}")
        print(f"  Final CR: {stats['cr']*100:.1f}%")
        print(f"  Final CD: {stats['cd']*100:.1f}%")
        print(f"  Final SPD: {stats['spd']:.0f}")
        print("-" * 30)

if __name__ == "__main__":
    compare_lin()
