
import json
import os
import sys

# Add project root to path to import Core modules
sys.path.append(os.getcwd())

from Core.models import Modifier, ModifierType, StatType, Character
from Core.data_loader import extract_json_from_md

def simulate(cr_val, cd_val, spd_bonus, atk_substat_p, use_blessing=True, use_journeys=True):
    with open("Data/characters.json", "r", encoding="utf-8") as f:
        specs = json.load(f)
    
    cname = "샤를(바니걸)(패시브1lv)"
    cdata = specs[cname]
    rotations = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    rdata = rotations[cname]
    
    # 1. Base Stats
    char = Character(cname, cdata["분류"], {
        StatType.ATK: cdata["기본_스탯"]["공격력"],
        StatType.SPEED: cdata["기본_스탯"]["속도"],
        StatType.CRIT_RATE: cr_val,
        StatType.CRIT_DAMAGE: cd_val,
        StatType.HP: 0.0
    })
    
    # 2. Add Journey Bonuses (Constant flat/percent increments)
    if use_journeys:
        # Top 5: No Pain (+6% ATK, +6% CR), Pavilion (+8% ATK), Petra (+18% CR), Indomitable (+12% CD), Kira (+30 Spd)
        cur_jr_cr = 0.06 + 0.18
        cur_jr_atk = 0.06 + 0.08
        cur_jr_cd = 0.12
        cur_jr_spd = 30
    else:
        cur_jr_cr = cur_jr_atk = cur_jr_cd = cur_jr_spd = 0
    
    res = cdata.get("공명", {})
    raw_pool = (cdata["기본_스탯"]["공격력"] + 1250)
    res_p = res.get("퍼센트", 0)
    res_flat = res.get("정수", 0)
    resonance_val = (raw_pool * res_p + res_flat)
    
    # static_atk_p: Substat + Grit 2-set + Journey ATK
    static_atk_p = atk_substat_p + 0.05 + cur_jr_atk
    eff_base = raw_pool * (1.0 + static_atk_p) + 1000
    
    TARGET_DEF_BASE = 3000.0
    total_dmg = 0.0
    cycle_time = 0.0
    ga_red_carry = 0.0
    attr_stack = 0
    ax_stack = 0
    
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
        
        # Blessing AX Tracking
        dyn_atk_p_sum = t.get("atk_buf", 0.0)
        if use_blessing:
            # AX: base 8% + 8% per action (max 5)
            # Stacks on every action, but check if it resets on ult (usually not for AX)
            # Actually AX is reset_on_ult: True (Line 405)
            ax_p = 0.08 + (ax_stack * 0.08)
            dyn_atk_p_sum += ax_p
            # Increment after action? No, stacks usually apply to current turn in this engine
            ax_stack = min(5, ax_stack + 1)
        
        eff_atk = eff_base * (1.0 + dyn_atk_p_sum) + resonance_val
        
        def_pen_total = t.get("def_pen_buf", 0.0)
        effective_def = TARGET_DEF_BASE * (1.0 - def_pen_total)
        def_multiplier = 1.0 - (effective_def / (effective_def + 3000.0))
        
        # Crit Stats including Journey
        final_cr = char.base_stats[StatType.CRIT_RATE] + cur_jr_cr + t.get("cr_buf", 0)
        final_cd = char.base_stats[StatType.CRIT_DAMAGE] + cur_jr_cd + t.get("cd_buf", 0)
        
        eff_cr = min(1.0, final_cr)
        eff_cd = final_cd
        
        total_di = t.get("di", 0.0)
        if is_ult:
            total_di += min(attr_stack * 0.05, 0.25)
            
        turn_dmg = (eff_atk * coeff * (1.0 + total_di + eff_cr * eff_cd)) * def_multiplier
        total_dmg += turn_dmg
        
        # Final Speed including Journey (+30 from Kira)
        final_spd = (char.base_stats[StatType.SPEED] + spd_bonus + cur_jr_spd) * t.get("spd_mult", 1.0)
        
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
            if use_blessing:
                ax_stack = 0 # AX Reset on Ult
            
    dps = total_dmg / cycle_time if cycle_time > 0 else 0
    return total_dmg, dps

if __name__ == "__main__":
    # Screenshot Baseline: Spd +66, CR 75.8%, CD 128.95%, ATK 20.3%
    cur_cr = 0.758
    cur_cd = 1.2895
    cur_spd_bonus = 66
    cur_atk_bonus = 0.203
    
    # 1. Without AX/Journeys (The one I showed before)
    dmg0, dps0 = simulate(cur_cr, cur_cd, cur_spd_bonus, cur_atk_bonus, use_blessing=False, use_journeys=False)
    
    # 2. With AX and Top 5 Journeys
    dmg1, dps1 = simulate(cur_cr, cur_cd, cur_spd_bonus, cur_atk_bonus, use_blessing=True, use_journeys=True)
    
    # 3. Swap Necklace Speed (33) -> ATK +16.5% (With AX/Journeys)
    dmg2, dps2 = simulate(cur_cr, cur_cd, 33, cur_atk_bonus + 0.165, use_blessing=True, use_journeys=True)
    
    print(f"DEBUG: Base Spec (No AX/Jr) | DPS: {dps0:.2f}")
    print(f"DEBUG: Full Build (AX+Jr)   | DPS: {dps1:.2f} | (+{((dps1/dps0)-1)*100:.1f}%)")
    print(f"DEBUG: Full Build (Swap ATK)| DPS: {dps2:.2f} | Change from Full Baseline: {((dps2/dps1)-1)*100:.1f}%")
