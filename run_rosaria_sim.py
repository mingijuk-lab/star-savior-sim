
import sys
import os
import json
import pandas as pd

# Add project root to path
sys.path.append(os.getcwd())

from Core.calc_dps import calculate_dps, setup_equipments, setup_journeys, setup_blessings
from Core.data_loader import extract_json_from_md

def run_rosaria_comparison():
    # 1. Load Data
    with open("Data/characters.json", "r", encoding="utf-8") as f:
        specs = json.load(f)
    
    rotations = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    
    # 2. Setup (using default baseline substats)
    substat_vars = {"$ATK$": 0.0, "$SPD$": 0.0, "$CR$": 0.0, "$CD$": 0.0}
    equipments = setup_equipments(substat_vars)
    
    cname = "로자리아"
    cdata = specs[cname]
    rdata = rotations[cname]
    
    results = []
    
    print(f"\n--- [Rosaria Simulation] ---")
    print(f"Basic Coeff: {cdata['스킬']['기본기']['계수']}")
    print(f"Special Coeff: {cdata['스킬']['특수기']['계수']}")
    print(f"Ultimate Coeff: {cdata['스킬']['궁극기']['계수']}")
    print("-" * 30)

    # Test major equipment sets
    test_sets = ["공격4+투지2", "통찰4+투지2", "파괴4+투지2"]
    
    # Common journey config for Rosaria (Ranger)
    best_jrs = ["노페인 노게인", "누각 위, 유리달 맞이", "불굴의 역작", "깊은 애도", "피의 메아리"]
    blessing = "AX"
    
    for eq_name in test_sets:
        if eq_name not in equipments: continue
        
        # Standard Rotation
        dps_15t, total_dmg, _, _, _ = calculate_dps(cname, cdata, rdata, eq_name, best_jrs, blessing, 15, False, equipments)
        results.append({
            "Equip": eq_name,
            "DPS (15T)": dps_15t,
            "Total Damage": total_dmg
        })
        print(f" > {eq_name}: {dps_15t:,.2f}")

    print("\n[OK] Simulation complete.")

if __name__ == "__main__":
    run_rosaria_comparison()
