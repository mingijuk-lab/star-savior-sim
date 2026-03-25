import pandas as pd
import numpy as np
from Core.models import StatType, Modifier, ModifierType, Character
from Core.data_loader import extract_json_from_md, load_equipments_from_json
from Core.calc_dps import calculate_dps, JOURNEYS, setup_equipments, find_best_journeys, get_interactive_substats
import Core.calc_dps as c_dps

def sweep_gear_performance(character_name, stat_type, max_val=0.30, steps=15):
    """
    Sweeps a specific sub-stat total from 0 to max_val and finds the best gear set.
    """
    # 1. Setup specs
    specs, rotations = extract_json_from_md("Data/캐릭터_스펙_마스터.md"), extract_json_from_md("Data/사이클_로테이션_마스터.md")
    if character_name not in specs: return
    
    cdata, rdata = specs[character_name], rotations[character_name]
    char_class = cdata.get("분류", cdata.get("class", "Unknown"))
    
    # 2. Initialize default EQUIPMENTS to find best journeys
    default_vars = {"$ATK$": 0.0, "$SPD$": 0.0, "$CR$": 0.0, "$CD$": 0.0}
    c_dps.EQUIPMENTS = setup_equipments(default_vars)
    
    base_eq = list(c_dps.EQUIPMENTS.keys())[0]
    best_jrs, _ = find_best_journeys(character_name, char_class, cdata, rdata, base_eq, 5)
    
    # Sub-stat variable name mapping
    var_map = {StatType.ATK: "$ATK$", StatType.SPEED: "$SPD$", StatType.CRIT_RATE: "$CR$", StatType.CRIT_DAMAGE: "$CD$"}
    target_var = var_map.get(stat_type)
    stat_label = {StatType.ATK: "공격력%", StatType.SPEED: "속도", StatType.CRIT_RATE: "치명타확률", StatType.CRIT_DAMAGE: "치명타피해"}[stat_type]
    
    report_lines = []
    report_lines.append(f"\n### [분석 대상: {character_name} | 분석 스탯: {stat_label}]")
    report_lines.append(f"- 범위: 0.0 ~ {max_val} (총 수치)")
    
    import Core.calc_dps
    original_equipments = c_dps.EQUIPMENTS
    
    current_best = None
    for val in np.linspace(0, max_val, steps + 1):
        per_piece_val = val / 6.0
        vars = {"$ATK$": 0.0, "$SPD$": 0.0, "$CR$": 0.0, "$CD$": 0.0}
        vars[target_var] = per_piece_val
        
        local_equipments = load_equipments_from_json("Data/equipments.json", vars)
        c_dps.EQUIPMENTS = local_equipments
        
        best_set, best_dps = None, -1
        for eq_name in local_equipments.keys():
            dps, _, _, _ = calculate_dps(character_name, cdata, rdata, eq_name, best_jrs, 10)
            if dps > best_dps:
                best_dps, best_set = dps, eq_name
        
        if best_set != current_best:
            line = f" > 총 {stat_label} +{val*100:4.1f}% 지점: 최적 = [{best_set}] (DPS: {best_dps:,.0f})"
            print(line)
            report_lines.append(line)
            current_best = best_set
            
    c_dps.EQUIPMENTS = original_equipments
    return report_lines

if __name__ == "__main__":
    import sys
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    full_report = ["# 장비 세트별 민감도 분석 리포트 (Sensitivity Analysis)\n"]
    full_report.append(f"> 한계 수치: 30% (Total Sum)\n")

    for char in ["로자리아", "유미나"]:
        print(f"\n{'='*20} {char} 최적화 분석 {'='*20}")
        full_report.append(f"## {char} 분석 결과")
        full_report.extend(sweep_gear_performance(char, StatType.CRIT_RATE))
        full_report.extend(sweep_gear_performance(char, StatType.CRIT_DAMAGE))
        full_report.extend(sweep_gear_performance(char, StatType.ATK))
        full_report.append("\n---\n")

    with open("Results/sensitivity_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(full_report))
    
    print(f"\n[OK] 분석 완료. 결과가 Results/sensitivity_report.md 에 저장되었습니다.")
