import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from Core.calc_engine_v5 import calculate_dps
from Core.data_loader_v5 import extract_json_from_md

def test_omega_mechanics():
    print("=== Testing Omega Stacking Mechanics ===")
    
    # Load data
    specs = extract_json_from_md("Data/캐릭터_스펙_마스터.md")
    rotations = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    
    omega_solo = specs.get("오메가")
    omega_party = specs.get("오메가(별속성파티)")
    rot = rotations.get("오메가")
    
    if not omega_solo or not rot:
        print("Error: Omega data not found.")
        return

    # Mock EQUIPMENTS
    import Core.calc_engine_v5 as engine
    engine.EQUIPMENTS = engine.setup_equipments({
        "$ATK$": 0.051, "$SPD$": 4.0, "$CR$": 0.033, "$CD$": 0.066
    })
    engine.JOURNEYS = {}
    engine.BLESSINGS = {}

    print("\n[Solo Performance Test]")
    eq_key = "공격4+투지2"
    if eq_key not in engine.EQUIPMENTS:
        eq_key = list(engine.EQUIPMENTS.keys())[0]
    print(f"Using Equipment: {eq_key}")
    
    dps_solo, _, _, _, _, _ = calculate_dps("오메가", omega_solo, rot, eq_key, [], max_actions=15, target_count=1)
    print(f"Omega Solo DPS: {dps_solo:,.2f}")

    print("\n[Star Party Performance Test]")
    dps_party, _, _, _, _, _ = calculate_dps("오메가(별속성파티)", omega_party, rot, eq_key, [], max_actions=15, target_count=1, force_star_party=True)
    print(f"Omega Star Party DPS: {dps_party:,.2f}")

    if dps_party > dps_solo:
        print("\nSUCCESS: Star Party DPS is higher than Solo DPS (as expected due to faster Power-up Star stacking).")
    else:
        print("\nFAILURE: Star Party DPS should be higher than Solo DPS.")

if __name__ == "__main__":
    test_omega_mechanics()
