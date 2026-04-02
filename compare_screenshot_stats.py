
import json
import os
import sys

# Add project root to path to import Core modules
sys.path.append(os.getcwd())

from Core.models import Modifier, ModifierType, StatType, Character
from Core.data_loader import extract_json_from_md

def simulate(cr_val, cd_val, spd_bonus, atk_substat_p):
    with open("Data/characters.json", "r", encoding="utf-8") as f:
        specs = json.load(f)
    
    cname = "샤를(바니걸)(패시브1lv)"
    cdata = specs[cname]
    rotations = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    rdata = rotations[cname]
    
    char = Character(cname, cdata["분류"], {
        StatType.ATK: cdata["기본_스탯"]["공격력"],
        StatType.SPEED: cdata["기본_스탯"]["속도"],
        StatType.CRIT_RATE: cr_val,
        StatType.CRIT_DAMAGE: cd_val,
        StatType.HP: 0.0
    })
    
    res = cdata.get("공명", {})
    raw_pool = (cdata["기본_스탯"]["공격력"] + 1250)
    res_p = res.get("퍼센트", 0)
    res_flat = res.get("정수", 0)
    resonance_val = (raw_pool * res_p + res_flat)
    
    static_atk_p = atk_substat_p + 0.05 # User ATK% + Grit 2-set
    eff_base = raw_pool * (1.0 + static_atk_p) + 1000
    
    TARGET_DEF_BASE = 3000.0
    total_dmg = 0.0
    cycle_time = 0.0
    ga_red_carry = 0.0
    attr_stack = 0
    
    max_actions = 15
    turns = rdata["turns"]
    
    for action_idx in range(min(len(turns), max_actions)):
        t = turns[action_idx]
        is_ult = t.get("is_ult", False)
        is_basic = t.get("is_basic", False)
        is_extra_attack = t.get("is_extra_attack", False)
        is_extra_turn = t.get("is_extra_turn", False)
        coeff = t.get("coeff", 0)
        
        if is_basic:
            attr_stack = min(5, attr_stack + 1)
        
        dyn_atk_p_sum = t.get("atk_buf", 0.0) 
        eff_atk = eff_base * (1.0 + dyn_atk_p_sum) + resonance_val
        
        def_pen_total = t.get("def_pen_buf", 0.0)
        effective_def = TARGET_DEF_BASE * (1.0 - def_pen_total)
        def_multiplier = 1.0 - (effective_def / (effective_def + 3000.0))
        
        final_cr = char.base_stats[StatType.CRIT_RATE] + t.get("cr_buf", 0)
        final_cd = char.base_stats[StatType.CRIT_DAMAGE] + t.get("cd_buf", 0)
        
        eff_cr = min(1.0, final_cr)
        eff_cd = final_cd
        
        total_di = t.get("di", 0.0)
        if is_ult:
            total_di += min(attr_stack * 0.05, 0.25)
            
        turn_dmg = (eff_atk * coeff * (1.0 + total_di + eff_cr * eff_cd)) * def_multiplier
        total_dmg += turn_dmg
        
        final_spd = (char.base_stats[StatType.SPEED] + spd_bonus) * t.get("spd_mult", 1.0)
        
        if not is_extra_attack:
            if is_extra_turn:
                turn_time = 0.0
            else:
                eff_ga = min(ga_red_carry, 0.99)
                turn_time = (1000.0 / final_spd) * (1.0 - eff_ga)
            cycle_time += turn_time
            ga_red_carry = 0.0
        
        ga_red_carry += t.get("ag_boost", 0.0)
        if (is_basic or is_extra_attack):
            ga_red_carry += 0.06
        if is_ult:
            ga_red_carry += 0.30
            attr_stack = 0
            
    dps = total_dmg / cycle_time if cycle_time > 0 else 0
    return total_dmg, dps

if __name__ == "__main__":
    # Updated Baseline: Speed 156 (90+66 - Neck 33 + Shoes 33), CR 75.8%, CD 128.95%, ATK bonus ~20.3%
    cur_cr = 0.758
    cur_cd = 1.2895
    cur_spd_bonus = 66
    cur_atk_bonus = 0.203
    
    dmg0, dps0 = simulate(cur_cr, cur_cd, cur_spd_bonus, cur_atk_bonus)
    print(f"DEBUG: Updated Baseline (+66) | Dmg: {dmg0:,.0f} | DPS: {dps0:.2f}")
    
    # 1. Swap Neck Speed (33) -> ATK +16.5% (Remaining Spd Bonus 33 (Shoes), ATK Bonus 20.3+16.5=36.8%)
    dmg1, dps1 = simulate(cur_cr, cur_cd, 33, cur_atk_bonus + 0.165)
    print(f"DEBUG: 1. Speed -> ATK+   | Dmg: {dmg1:,.0f} | DPS: {dps1:.2f} | Change: {((dps1/dps0)-1)*100:.1f}%")
    
    # 2. Swap Neck Speed (33) -> CR +16% (Remaining Spd Bonus 33 (Shoes), CR 75.8+16=91.8%)
    dmg2, dps2 = simulate(cur_cr + 0.16, cur_cd, 33, cur_atk_bonus)
    print(f"DEBUG: 2. Speed -> CR+    | Dmg: {dmg2:,.0f} | DPS: {dps2:.2f} | Change: {((dps2/dps0)-1)*100:.1f}%")
    
    # 3. Swap Neck Speed (33) -> CD +17.8% (Remaining Spd Bonus 33 (Shoes), CD 128.95+17.8=146.75%)
    dmg3, dps3 = simulate(cur_cr, cur_cd + 0.178, 33, cur_atk_bonus)
    print(f"DEBUG: 3. Speed -> CD+    | Dmg: {dmg3:,.0f} | DPS: {dps3:.2f} | Change: {((dps3/dps0)-1)*100:.1f}%")
