
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
    
    static_atk_p = atk_substat_p + 0.05 # Substat + Grit 2-set
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
    # Baseline: Spd +66, CR 93.1%, CD 113.55%
    dmg_base, dps_base = simulate(0.931, 1.1355, 66, 0.165)
    
    # Scenario A: Spd +33, CR 93.1% + 15.5% = 108.6% (Cap 100%), CD 113.55%
    dmg_a, dps_a = simulate(0.931 + 0.155, 1.1355, 33, 0.165)
    
    # Scenario B: Spd +33, CR 93.1%, CD 113.55% + 16.5% = 130.05%
    dmg_b, dps_b = simulate(0.931, 1.1355 + 0.165, 33, 0.165)
    
    print(f"DEBUG: Baseline (Spd 66)  TotalDmg: {dmg_base:,.0f} | DPS: {dps_base:.2f}")
    print(f"DEBUG: Scenario A (CR Swap) TotalDmg: {dmg_a:,.0f} | DPS: {dps_a:.2f}")
    print(f"DEBUG: Scenario B (CD Swap) TotalDmg: {dmg_b:,.0f} | DPS: {dps_b:.2f}")
