import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Core.calc_dps import calculate_dps, extract_json_from_md, EQUIPMENTS

def run_efficiency_study():
    cdata_all = extract_json_from_md("Data/캐릭터_스펙_마스터.md")
    rdata_all = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    
    cname = "로자리아"
    cdata = cdata_all[cname]
    rdata = rdata_all[cname]
    
    arc_name = "레인저B"
    jr_name = "AX"
    
    import Core.calc_dps
    Core.calc_dps.EQUIPMENTS["없음"] = {"atk": 0.0, "cr": 0.0, "cd": 0.0, "spd": 0}
    
    turns_to_test = [15, 50, 100]
    
    print(f"--- Rosaria Attack Set Efficiency Study ({arc_name}) ---")
    print(f"{'Turns':<10} | {'No Set DPS':<15} | {'Atk Set DPS':<15} | {'Real Increase (%)':<15}")
    print("-" * 65)
    
    for t in turns_to_test:
        # calculate_dps returns (dps, total_dmg, cycle_time, max_hit)
        res_no = calculate_dps(cname, cdata, rdata, "없음", arc_name, jr_name, t)
        res_atk = calculate_dps(cname, cdata, rdata, "공격4세트", arc_name, jr_name, t)
        
        dps_no = res_no[0]
        dps_atk = res_atk[0]
        
        increase = ((dps_atk / dps_no) - 1) * 100
        print(f"{t:<10} | {dps_no:<15.2f} | {dps_atk:<15.2f} | {increase:<15.2f}%")

if __name__ == "__main__":
    run_efficiency_study()
