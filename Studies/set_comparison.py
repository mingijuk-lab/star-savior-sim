import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Core.calc_dps import calculate_dps, extract_json_from_md, EQUIPMENTS

def run_full_comparison_study():
    cdata_all = extract_json_from_md("Data/캐릭터_스펙_마스터.md")
    rdata_all = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    
    cname = "로자리아"
    cdata = cdata_all[cname]
    rdata = rdata_all[cname]
    
    jr_name = "AX"
    
    import Core.calc_dps
    Core.calc_dps.EQUIPMENTS["없음"] = {"atk": 0.0, "cr": 0.0, "cd": 0.0, "spd": 0}
    
    arcanas = ["레인저A", "레인저B", "레인저C", "레인저D"]
    sets = ["공격4세트", "통찰4세트", "파괴4세트"]
    
    print(f"--- Rosaria Comprehensive Equipment Efficiency Study ---")
    print("-" * 85)
    
    for arc in arcanas:
        print(f"\n[ Arcana: {arc} ]")
        print(f"{'Set Name':<15} | {'DPS':<15} | {'Real Increase (%)':<15}")
        print("-" * 50)
        
        # Baseline
        res_no = calculate_dps(cname, cdata, rdata, "없음", arc, jr_name, 15)
        dps_no = res_no[0]
        print(f"{'No Set':<15} | {dps_no:<15.2f} | 0.00%")
        
        for s in sets:
            res = calculate_dps(cname, cdata, rdata, s, arc, jr_name, 15)
            dps = res[0]
            increase = ((dps / dps_no) - 1) * 100
            print(f"{s:<15} | {dps:<15.2f} | {increase:<15.2f}%")

if __name__ == "__main__":
    run_full_comparison_study()
