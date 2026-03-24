import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Core.calc_dps import calculate_dps, extract_json_from_md, EQUIPMENTS

def run_peak_hit_study():
    cdata_all = extract_json_from_md("Data/캐릭터_스펙_마스터.md")
    rdata_all = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    
    cname = "로자리아"
    cdata = cdata_all[cname]
    rdata = rdata_all[cname]
    
    jr_name = "AX"
    
    arcanas = ["레인저A", "레인저B", "레인저C", "레인저D"]
    sets = ["공격4세트", "통찰4세트", "파괴4세트"]
    
    print(f"--- Rosaria Peak Hit (Single Strongest Damage) Study ---")
    print("-" * 75)
    
    for arc in arcanas:
        print(f"\n[ Arcana: {arc} ]")
        print(f"{'Set Name':<15} | {'Peak Hit DMG':<20} | {'Rel. Strength (%)':<15}")
        print("-" * 60)
        
        # We'll use the Attack set of each arc as the baseline for 'Rel. Strength' within that arc
        res_atk = calculate_dps(cname, cdata, rdata, "공격4세트", arc, jr_name, 50)
        base_peak = res_atk[3] # max_hit
        
        for s in sets:
            res = calculate_dps(cname, cdata, rdata, s, arc, jr_name, 50)
            peak = res[3]
            rel = (peak / base_peak) * 100
            print(f"{s:<15} | {peak:<20.2f} | {rel:<15.2f}%")

if __name__ == "__main__":
    run_peak_hit_study()
