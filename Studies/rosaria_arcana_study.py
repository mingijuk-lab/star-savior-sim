import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from Core.calc_dps import calculate_dps, extract_json_from_md

def run_study():
    specs = extract_json_from_md("Data/캐릭터_스펙_마스터.md")
    rotations = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    
    cname = "로자리아"
    cdata = specs[cname]
    rdata = rotations[cname]
    
    arcanas = ["레인저A", "레인저B", "레인저C", "레인저D"]
    equipments = ["공격4세트", "통찰4세트", "파괴4세트", "속도4세트"]
    journey = "AX"     # Standard assumption
    
    print(f"--- Rosaria Ultra-Short Burst Study ---")
    print(f"Journey: {journey}")
    print("-" * 65)
    
    turn_range = [5, 10, 15, 20, 50, 100]
    
    for eq in equipments:
        print(f"\n[ Equipment: {eq} ]")
        print(f"{'Turns':<10} | {'Ranger A':<11} | {'Ranger B':<11} | {'Ranger C':<11} | {'Ranger D':<11}")
        print("-" * 65)
        for turns in turn_range:
            row = f"{turns:<10} | "
            for arc in arcanas:
                dps, total, time, max_hit = calculate_dps(cname, cdata, rdata, eq, arc, journey, max_actions=turns)
                row += f"{dps:<11.2f} | "
            print(row)

if __name__ == "__main__":
    run_study()
