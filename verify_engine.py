import json
import os
import sys
import Core.calc_engine_v5 as engine

def verify():
    print("--- Stacks Verification ---")
    
    # 1. Load Data
    try:
        with open("Data/characters.json", "r", encoding="utf-8") as f:
            specs = json.load(f)
    except:
        specs = engine.extract_json_from_md("Data/캐릭터_스펙_마스터.md")
        
    rotations = engine.extract_json_from_md("Data/사이클_로테이션_마스터.md")
    
    # 2. Setup Equipments
    substat_vars = {
        "$ATK$": 0.0, 
        "$SPD$": 0.0, 
        "$CR$": 0.0, 
        "$CD$": 0.0, 
        "METRIC": 1
    }
    # IMPORTANT: setup_equipments returns a registry, so we must assign it to the global
    engine.EQUIPMENTS = engine.setup_equipments(substat_vars)
    
    # Access populated global dict
    if not engine.EQUIPMENTS:
        print("  - Error: EQUIPMENTS not initialized!")
        return
        
    eq_name = list(engine.EQUIPMENTS.keys())[0]
    print(f"Using test equipment: {eq_name}")
    
    # Test cases: Frey (Moon Party) and Claire
    test_cases = ["프레이(달속성파티)", "클레어(바니걸)"]
    
    for cname in test_cases:
        print(f"\n[Character: {cname}]")
        cdata = specs.get(cname)
        rdata = rotations.get(cname)
        
        if not cdata or not rdata:
            print("  - Data missing!")
            continue
            
        # Run 15 turn simulation
        # Using empty journals [] to check baseline with new stack logic
        dps, dmg, time, _, max_h, stats = engine.calculate_dps(
            cname, cdata, rdata, eq_name, [], None, 15, False
        )
        
        print(f"  - DPS: {dps:,.2f}")
        print(f"  - Total Damage: {dmg:,.0f}")
        print(f"  - Max Hit: {max_h:,.0f}")
        print(f"  - Calculated actions: {len(rdata['turns'][:15])}")

if __name__ == "__main__":
    verify()
