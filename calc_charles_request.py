
import json
import os
import sys

# Add project root to path to import Core modules
sys.path.append(os.getcwd())

from Core.models import Modifier, ModifierType, StatType, Character
from Core.data_loader import extract_json_from_md

def calculate_charles_dps():
    # 1. Load Character Data
    with open("Data/characters.json", "r", encoding="utf-8") as f:
        specs = json.load(f)
    
    cname = "샤를(바니걸)(패시브1lv)"
    cdata = specs[cname]
    
    # 2. Load Rotation Data
    rotations = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    rdata = rotations[cname]
    
    # 3. Setup Character with User Stats
    # The user provided FINAL stats (93.1% CR, 113.55% CD)
    # We will use these as the base for the simulation to avoid double-counting equipment.
    char = Character(cname, cdata["분류"], {
        StatType.ATK: cdata["기본_스탯"]["공격력"],
        StatType.SPEED: cdata["기본_스탯"]["속도"],
        StatType.CRIT_RATE: 0.931 + 0.155,
        StatType.CRIT_DAMAGE: 1.1355 + 0.165,
        StatType.HP: 0.0
    })
    
    # Add standard multipliers from calc_dps.py logic
    # raw_pool calculation: (BaseAtk + 1250) * Resonance% + ResonanceFlat
    res = cdata.get("공명", {})
    raw_pool = (cdata["기본_스탯"]["공격력"] + 1250)
    res_p = res.get("퍼센트", 0)
    res_flat = res.get("정수", 0)
    resonance_val = (raw_pool * res_p + res_flat)
    
    # static_atk_p: User corrected to 16.5% ATK substat (single ring) + Grit 2-set (5%)
    static_atk_p = 0.165 + 0.05
    eff_base = raw_pool * (1.0 + static_atk_p) + 1000
    
    # Constants from calc_dps.py
    TARGET_DEF_BASE = 3000.0
    FINAL_GENERIC_MULT = 1.1
    
    total_dmg = 0.0
    cycle_time = 0.0
    ga_red_carry = 0.0
    attr_stack = 0
    
    max_actions = 15
    turns = rdata["turns"]
    
    print(f"--- Star Savior DPS Simulation: {cname} ---")
    print(f"Target CR: {char.base_stats[StatType.CRIT_RATE]*100:.2f}%")
    print(f"Target CD: {char.base_stats[StatType.CRIT_DAMAGE]*100:.2f}%")
    print(f"Effective Base ATK: {eff_base:.2f}")
    print(f"Resonance Value: {resonance_val:.2f}")
    print("-" * 40)
    
    for action_idx in range(min(len(turns), max_actions)):
        t = turns[action_idx]
        is_ult = t.get("is_ult", False)
        is_basic = t.get("is_basic", False)
        is_spec = (not is_basic) and (not is_ult) and (not t.get("is_extra", False))
        is_extra_attack = t.get("is_extra_attack", False)
        is_extra_turn = t.get("is_extra_turn", False)
        
        coeff = t.get("coeff", 0)
        
        # 1. Update Attribute Stack (Universal Rule: Basic +1)
        if is_basic:
            attr_stack = min(5, attr_stack + 1)
        
        # 2. Dynamic ATK Multipliers (v14.3 logic)
        dyn_atk_p_sum = t.get("atk_buf", 0.0) 
        # Charles Assassin doesn't have other dynamic atk stacks in this simplified model
        
        eff_atk = eff_base * (1.0 + dyn_atk_p_sum) + resonance_val
        
        # 3. Defense Calculation
        def_pen_total = t.get("def_pen_buf", 0.0) # Lucky Token gives 20%
        effective_def = TARGET_DEF_BASE * (1.0 - def_pen_total)
        def_multiplier = 1.0 - (effective_def / (effective_def + 3000.0))
        
        # 4. Final Stats
        # Since we used the final CR/CD as base, and t.get("cr_buf") etc is usually 0 here:
        final_cr = char.base_stats[StatType.CRIT_RATE] + t.get("cr_buf", 0)
        final_cd = char.base_stats[StatType.CRIT_DAMAGE] + t.get("cd_buf", 0)
        
        eff_cr = min(1.0, final_cr)
        eff_cd = final_cd
        
        # 5. Damage Calculation
        total_di = t.get("di", 0.0)
        if is_ult:
            # Ult bonus: +5% dmg per stack (max 5)
            total_di += min(attr_stack * 0.05, 0.25)
            # After Ult, stack is cleared
            
        turn_dmg = (eff_atk * coeff * (1.0 + total_di + eff_cr * eff_cd)) * def_multiplier
        total_dmg += turn_dmg
        
        # 6. Time Calculation
        # User swapped Necklace Speed (33) for CR/CD. Only Boots (33) remains.
        final_spd = (char.base_stats[StatType.SPEED] + 33) * t.get("spd_mult", 1.0)
        
        if not is_extra_attack:
            if is_extra_turn:
                turn_time = 0.0
            else:
                eff_ga = min(ga_red_carry, 0.99)
                turn_time = (1000.0 / final_spd) * (1.0 - eff_ga)
            cycle_time += turn_time
            ga_red_carry = 0.0
        
        # Register AG reduction
        ga_red_carry += t.get("ag_boost", 0.0)
        # Passive AG (Level 1 is 0.06)
        if (is_basic or is_extra_attack):
            ga_red_carry += 0.06
        if is_ult:
            # charles ult note: "자신의 행동 게이지 30% 증가."
            ga_red_carry += 0.30
        
        if is_ult:
            attr_stack = 0 # Clear after ult
            
        print(f"[T{action_idx+1}] {t.get('note', '')[:15]:15} | Dmg: {turn_dmg:,.0f} | Time: {turn_time:.2f}s | AG Carry: {ga_red_carry:.2f}")

    dps = total_dmg / cycle_time if cycle_time > 0 else 0
    print("-" * 40)
    print(f"Total Damage: {total_dmg:,.0f}")
    print(f"Cycle Time:   {cycle_time:.2f}s")
    print(f"FINAL DPS:    {dps:,.2f}")
    return dps

if __name__ == "__main__":
    calculate_charles_dps()
