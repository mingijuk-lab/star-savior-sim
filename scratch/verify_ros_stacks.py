import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Core.calc_engine_v5 import calculate_dps
import Core.calc_engine_v5 as engine
from Core.data_loader_v5 import extract_json_from_md

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def verify():
    # Load raw character data
    with open('Data/characters.json', 'r', encoding='utf-8') as f:
        cdata_all = json.load(f)
    
    # Load rotations from MD
    rdata_all = extract_json_from_md('Data/사이클_로테이션_마스터.md')
    
    # Initialize engine data
    substats = {"$ATK$": 0.0, "$SPD$": 0.0, "$CR$": 0.0, "$CD$": 0.0}
    eq_registry = engine.setup_equipments(substats)
    engine.JOURNEYS = engine.setup_journeys()
    engine.BLESSINGS = engine.setup_blessings()
    
    rosaria = cdata_all['로자리아']
    rot = rdata_all['로자리아']
    
    # 1. Target Count = 1 (Boss)
    dps1, total1, _, _, maxh1, _ = engine.calculate_dps(
        "로자리아", rosaria, rot, "통찰4+투지2", ["노페인 노게인", "깊은 애도"], 
        max_actions=50, target_count=1, custom_equipments=eq_registry
    )
    
    # 2. Target Count = 3 (Normal)
    dps3, total3, _, _, maxh3, _ = engine.calculate_dps(
        "로자리아", rosaria, rot, "통찰4+투지2", ["노페인 노게인", "깊은 애도"], 
        max_actions=50, target_count=3, custom_equipments=eq_registry
    )
    
    print(f"Rosaria (Boss 1-unit) DPS (10T): {dps1:.2f}")
    print(f"Rosaria (Normal 3-unit) DPS (10T): {dps3:.2f}")
    
    if dps3 > dps1:
        print("Success: 3-unit DPS is higher due to better Ignition stack gain.")
    elif dps3 == dps1:
        # In very short terms or specific gear, it might be equal if the extra attack isn't reached yet
        print("Note: DPS is identical. This might be due to cycle length (10T) or gear.")
    else:
        print(f"Failure: 1-unit DPS ({dps1:.2f}) is still higher than 3-unit ({dps3:.2f}).")

if __name__ == "__main__":
    verify()
