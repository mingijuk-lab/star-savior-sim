import sys
import os
import json
import itertools
from Core.models import Modifier, ModifierType, StatType, EquipmentPiece, EquipmentSet, Journey, Character
from Core.data_loader import load_equipments_from_json, load_journeys_from_json, load_blessings_from_json, extract_json_from_md
from Core.gear_sensitivity import profile_stat_scaling
import numpy as np
import pandas as pd

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def get_interactive_substats():
    if not sys.stdin.isatty():
        return {"$ATK$": 0.0, "$SPD$": 0.0, "$CR$": 0.0, "$CD$": 0.0}

    print("\n" + "="*50)
    print(" [Star Savior] 장비 부옵션 설정")
    print(" - 직접 입력하려면 숫자를 입력하고, 기본값을 쓰려면 Enter를 누르세요.")
    print("="*50)
    def ask(msg, default):
        val = input(f" {msg} (기본 {default}): ").strip()
        return float(val) if val else default
    
    return {
        "$ATK$": ask("공격력% 부옵 (예: 0.051)", 0.051),
        "$SPD$": ask("속도 부옵    (예: 4.0)", 4.0),
        "$CR$":  ask("치명타확률 부옵 (예: 0.033)", 0.033),
        "$CD$":  ask("치명타피해 부옵 (예: 0.066)", 0.066),
        "METRIC": ask("최적화 기준 (1: DPS, 2: 총 데미지)", 2)
    }

def setup_equipments(substat_vars=None):
    # Strip METRIC before passing to loader
    vars_only = {k:v for k,v in substat_vars.items() if k.startswith("$")} if substat_vars else None
    try:
        registry = load_equipments_from_json("Data/equipments.json", vars_only)
        return registry
    except Exception as e:
        print(f"Warning: Could not load Data/equipments.json ({e}). Using hardcoded fallback.")
        return {
            "공격4세트": EquipmentSet("공격4세트", {"weapon": EquipmentPiece("weapon", "weapon", [Modifier(StatType.ATK, 0.20, ModifierType.PERCENT)])}),
            "통찰4세트": EquipmentSet("통찰4세트", {"weapon": EquipmentPiece("weapon", "weapon", [Modifier(StatType.CRIT_RATE, 0.30, ModifierType.FLAT)])}),
            "파괴4세트": EquipmentSet("파괴4세트", {"weapon": EquipmentPiece("weapon", "weapon", [Modifier(StatType.CRIT_DAMAGE, 0.40, ModifierType.FLAT)])}),
            "속도4세트": EquipmentSet("속도4세트", {"weapon": EquipmentPiece("weapon", "weapon", [Modifier(StatType.SPEED, 15, ModifierType.FLAT)])}),
            "체력4세트": EquipmentSet("체력4세트", {"weapon": EquipmentPiece("weapon", "weapon", [Modifier(StatType.HP, 0.30, ModifierType.PERCENT)])}),
        }

def setup_journeys():
    try:
        from Core.data_loader import load_journeys_from_json
        return load_journeys_from_json("Data/equipments.json")
    except Exception as e:
        print(f"Warning: Could not load Journeys from Data/equipments.json ({e}). Using hardcoded fallback.")
        return {
            "노페인 노게인": Journey("노페인 노게인", [Modifier(StatType.ATK, 0.06, ModifierType.PERCENT)], "EX"),
        }

EQUIPMENTS = {} 
JOURNEYS = setup_journeys()
BLESSINGS = {} # Populated in main or setup

def setup_blessings():
    try:
        from Core.data_loader import load_blessings_from_json
        return load_blessings_from_json("Data/equipments.json")
    except Exception as e:
        print(f"Warning: Could not load Blessings ({e})")
        return {}

BLESSINGS = setup_blessings()

def calculate_dps(cname, cdata, rdata, eq_name, jr_names, blessing_name=None, max_actions=15, force_no_ult=False, custom_equipments=None):
    """
    Main simulation engine for damage calculation.
    Supports turns, hits, buffs, and dynamic passive stacking.
    """
    if custom_equipments:
        eq = custom_equipments[eq_name]
    else:
        eq = EQUIPMENTS[eq_name]
    
    if isinstance(jr_names, str): jr_names = [jr_names]
    jrs = [JOURNEYS[j] for j in jr_names if j in JOURNEYS]
    
    # Add blessing to the modifier list
    blessing = BLESSINGS.get(blessing_name)
    if blessing:
        jrs.append(blessing)
    
    res = cdata.get("공명", {})
    
    # Initialize Character object
    char_class = cdata.get("분류", cdata.get("class", "Unknown"))
    char = Character(cname, char_class, {
        StatType.ATK: cdata["기본_스탯"]["공격력"],
        StatType.SPEED: cdata["기본_스탯"]["속도"],
        StatType.CRIT_RATE: cdata["기본_스탯"]["치명타_확률"],
        StatType.CRIT_DAMAGE: cdata["기본_스탯"]["치명타_피해"],
        StatType.HP: cdata.get("기본_스탯", {}).get("체력", 0.0)
    })
    
    # 1. Base Resonance & System Flat
    char.add_permanent_modifier(Modifier(StatType.ATK, 1250, ModifierType.FLAT, "StellaArchive"))
    char.add_permanent_modifier(Modifier(StatType.ATK, res.get("퍼센트", 0), ModifierType.PERCENT, "Resonance%"))
    char.add_permanent_modifier(Modifier(StatType.ATK, res.get("정수", 0), ModifierType.FLAT, "ResonanceFlat"))
    
    # 2. Add Equipment & Journey modifiers
    for mod in eq.get_all_modifiers(): char.add_permanent_modifier(mod)
    for jr in jrs:
        for mod in jr.modifiers: char.add_permanent_modifier(mod)
    
    # 3. Add Substats & System Constant
    char.add_permanent_modifier(Modifier(StatType.ATK, 0.1625 + 0.01, ModifierType.PERCENT, "Substats"))
    char.add_permanent_modifier(Modifier(StatType.ATK, 1000, ModifierType.FLAT, "SystemConstant"))
    char.add_permanent_modifier(Modifier(StatType.SPEED, 60, ModifierType.FLAT, "SubstatsSpd"))
    
    # Passive Modifiers
    if "패시브" in cdata:
        p = cdata["패시브"]
        if "공격력_퍼센트" in p:
            char.add_permanent_modifier(Modifier(StatType.ATK, p["공격력_퍼센트"], ModifierType.PERCENT, "PassiveAtk"))
        if "치확_퍼센트" in p:
            char.add_permanent_modifier(Modifier(StatType.CRIT_RATE, p["치확_퍼센트"], ModifierType.FLAT, "PassiveCR"))
        if "치피_퍼센트" in p:
            char.add_permanent_modifier(Modifier(StatType.CRIT_DAMAGE, p["치피_퍼센트"], ModifierType.FLAT, "PassiveCD"))

    # Initial Stats (Check for AX in ANY journey)
    has_ax = (blessing_name == "AX")
    has_fx = (blessing_name == "FX")
    has_ex = (blessing_name == "EX")
    
    # Pre-calculate AX Stacks if needed
    ax_stacks = []
    if has_ax:
        cur_ax = 0
        for t in rdata["turns"]:
            cur_ax = min(cur_ax + 1, 5)
            ax_stacks.append(cur_ax)
            if t.get("is_ult", False) and not force_no_ult:
                cur_ax = 0
    
    total_dmg, cycle_time, ga_red_carry, omega_dmg_stack, assassin_spd_stack, caster_cd_stack, ra_cr_stack = 0.0, 0.0, 0, 0, 0, 0, 0
    fx_carry = 0.0
    ex_basic_count = 0
    ex_total_cr = 0.0
    frey_hr = 0
    frey_cr_turns = 0
    charles_lucky_token_turns = 0 # Track Charles's Lucky Token
    charles_atk_buff_turns = 0   # Track Charles's ATK 30% (2 turns)
    rosaria_def_pen_turns = 0    # Track Rosaria's DEF Pen (3 turns after Ult)
    smile_def_red_turns = 0 # Track Smile's DEF Red debuff
    lydia_atk_stack = 0     # Lydia's Passive (6% x 5)
    yumina_atk_stack = 0    # Yumina's Passive (4% x 5)
    bleeding_dots = []
    
    # Universal Attribute (속성) Stack
    attr_stack = 0
    # Rosaria Ignition (업화)
    is_rosaria = "로자리아" in cname
    ros_ign_stack = 0

    # v15.0 Dynamic Passive Stacks
    p_stacks = {"claire_cr": 0, "lydia_atk": 0, "yumina_atk": 0, "assera_cd": 0}
    is_yumina = "유미나" in cname
    is_frey = "프레이" in cname
    is_moon_party = "달속성파티" in cname
    is_jackpot = False
    y_is_1lv = "1lv" in cname
    y_crit_ga = 0.09 if y_is_1lv else 0.15
    y_atk_rate = 0.02 if y_is_1lv else 0.04

    rosa_atk_stack = 0
    
    turns = rdata["turns"]
    turns_count = len(turns)

    hits = [] # For calculating average crit chance for Blood Echo

    for action_idx in range(turns_count):
        if action_idx >= max_actions:
            break
        
        # 0. Prep action data
        t = turns[action_idx]
        
        is_ult = t.get("is_ult", False)
        if force_no_ult and is_ult:
            is_ult = False
            is_basic, is_spec, is_extra = True, False, False
            coeff = 1.65 # Treat as basic
        else:
            is_basic = t.get("is_basic", False)
            is_ult = t.get("is_ult", False)
            is_spec = (not is_basic) and (not is_ult) and (not t.get("is_extra", False))
            is_extra = t.get("is_extra", False)
            coeff = t.get("coeff", 0) + t.get("extra_coeff", 0)
        
        # Determine is_aoe from cdata (v26.0)
        curr_skill_type = "궁극기" if is_ult else ("기본기" if is_basic else "특수기")
        curr_skill = cdata.get("스킬", {}).get(curr_skill_type, {})
        is_aoe = "전체 공격" in curr_skill.get("부가", "")
        # Yumina Catalyst Exception: If Yumina's basic attack is used with "경력직 용병", it becomes AoE.
        if "유미나" in cname and is_basic and any(j.name == "경력직 용병" for j in jrs):
            is_aoe = True

        # Attribute Stack (Universal Rule: Basic +1)
        if is_basic:
            attr_stack = min(5, attr_stack + 1)
        
        # Rosaria Specific Logic
        rosaria_extra_basic = False
        if is_rosaria:
            # Ignition probability: Basic -> + (attr * 0.20)
            if is_basic:
                ros_ign_stack = min(5, ros_ign_stack + attr_stack * 0.20)
            # Spec uses Ignition
            if is_spec:
                ign_di = 0.0
                if ros_ign_stack >= 3.0:
                    ign_di = 0.20
                    rosaria_extra_basic = True
                    ros_ign_stack = 0
                elif ros_ign_stack >= 2.0:
                    ign_di = 0.20
                    ros_ign_stack = 0
                elif ros_ign_stack >= 1.0:
                    ign_di = 0.10
                    ros_ign_stack = 0
                m_di += ign_di
            # Ult gives Ignition +3
            if is_ult:
                ros_ign_stack = min(5, ros_ign_stack + 3)
        
        # Trigger Passives (v15.0 Dynamic Triggers)
        
        # 1. Turn-Start Triggers (Before time calculation)
        if "클레어(바니걸)" in cname:
            p_stacks["claire_cr"] = min(3, p_stacks["claire_cr"] + 1)
            
        # 2. Action-Start Triggers
        if "리디아" in cname:
            # Lydia: ATK +6% per action (max 5)
            p_stacks["lydia_atk"] = min(5, p_stacks["lydia_atk"] + 1)
        if "아세라" in cname and is_spec:
            # Assera: CD +6% per Special (max 5)
            p_stacks["assera_cd"] = min(5, p_stacks["assera_cd"] + 1)
        if is_yumina:
            # Yumina: ATK +4% per "Action/Hit" (simplified to per action for consistency, but user said hit)
            # We'll use 1 stack per action here for now unless it's multi-hit.
            p_stacks["yumina_atk"] = min(5, p_stacks["yumina_atk"] + 1)
            
        # Buff Application (Starts after Spec, so if it was set in PREVIOUS end-of-turn, it's active now)
        cr_from_buff = 0.30 if (is_frey and frey_cr_turns > 0) else 0.0
            
        # Stacking logic for specialized Journeys
        if any(j.name == "키라만큼 귀여워" for j in jrs): assassin_spd_stack = min(assassin_spd_stack + 1, 3)
        if any(j.name == "하늘의 심판" for j in jrs): caster_cd_stack = min(caster_cd_stack + 1, 3)
        if any(j.name == "깊은 애도" for j in jrs) and (is_basic or t.get("extra_coeff", 0) > 0):
            ra_cr_stack = min(ra_cr_stack + 1, 5)

        # 0. Defense Calculation (v14.2)
        target_def_base = 3000.0
        # Check for DEF Reduction (Smile's debuff or Journey)
        current_def_red = 0.30 if smile_def_red_turns > 0 else 0.0
        
        # DEF Penetration (stat-based + dynamic buffer)
        def_pen_total = char.get_stat(StatType.DEF_PEN, []) + t.get("def_pen_buf", 0.0)
            
        effective_def = target_def_base * (1.0 - current_def_red) * (1.0 - def_pen_total)
        def_multiplier = 1.0 - (effective_def / (effective_def + 3000.0))

        # Dynamic ATK Multipliers (now primarily in t['atk_buf'])
        m_di = 0.0

        dyn_mods = []
        if assassin_spd_stack > 0: dyn_mods.append(Modifier(StatType.SPEED, assassin_spd_stack * 10, ModifierType.FLAT, "AssassinStack"))
        
        final_spd = char.get_stat(StatType.SPEED, dyn_mods) * t.get("spd_mult", 1.0)
        
        # Extra Attack (TN+) / Extra Turn (TN+1) Logic
        if not t.get("is_extra_attack", False):
            is_extra_turn = t.get("is_extra_turn", False)
            if is_extra_turn:
                turn_time = 0.0
            else:
                eff_ga = min(ga_red_carry, 0.99) # 음수 방지
                turn_time = (1000.0 / final_spd) * (1.0 - eff_ga)
            cycle_time += turn_time
            ga_red_carry = 0.0 # Consume carry
            
        # Register next AG reduction if applicable
        if not force_no_ult:
            ga_red_carry += t.get("ag_boost", 0.0)
        
        if any(j.name == "허수의 개척자" for j in jrs):
            if is_spec: omega_dmg_stack = min(omega_dmg_stack + 1, 5)

        # Apply Character Passive Stacks to stat pools (v15.0)
        dyn_atk_p_sum = 0.0
        if "리디아" in cname: dyn_atk_p_sum += p_stacks["lydia_atk"] * 0.06
        if is_yumina: 
            y_atk_rate = 0.02 if y_is_1lv else 0.04
            dyn_atk_p_sum += p_stacks["yumina_atk"] * y_atk_rate
        
        # Collect DI and Buffs from turn data
        for k, v in t.items():
            if k.endswith("_di"): m_di += v
            if k.endswith("_atk_p"): dyn_atk_p_sum += v
        
        # 1. Raw Pool (Stella Archive only)
        raw_pool = (cdata["기본_스탯"]["공격력"] + 1250)
        
        # 2. Static ATK% (Equipment% + Journey% + Substats%)
        eq_jr_atk_p = 0.0
        for mod in char.permanent_modifiers:
            if mod.stat_type == StatType.ATK and mod.mod_type == ModifierType.PERCENT:
                # Exclude Resonance% and StellaArchive
                if mod.source not in ["Resonance%", "StellaArchive", "Substats", "SystemConstant"]:
                    eq_jr_atk_p += mod.value
        
        static_atk_p = eq_jr_atk_p + (0.1625 + 0.01) # Substats fixed %
        # Standard v14.1 eff_base: Resonance is excluded from multipliers
        eff_base = raw_pool * (1.0 + static_atk_p) + 1000
        
        # 3. Dynamic ATK and Multipliers (v14.3 Unified Summation)
        # Formula: eff_atk = eff_base * (1 + Σ(Dynamic_Atk_Buffs)) + resonance
        # Summing all dynamic buffs: AX + Json_Atk_Buf + Passive_Stacks + Multiplier_Effects
        
        res_p = res.get("퍼센트", 0)
        res_flat = res.get("정수", 0)
        resonance_val = (raw_pool * res_p + res_flat)
        
        # dyn_atk_p_sum is already initialized and populated by passive stacks
        if has_ax:
            dyn_atk_p_sum += ax_stacks[action_idx] * 0.08
            
        # 피의 메아리 (v26.0)
        if any(j.name == "피의 메아리" for j in jrs):
            dyn_atk_p_sum += rosa_atk_stack * 0.03
            
        # Final multiplicative formula for dynamic buffs
        eff_atk = eff_base * (1.0 + dyn_atk_p_sum) + resonance_val
        
        # Final Crit/CD Calculation including Passives (v15.0)
        final_cr = char.get_stat(StatType.CRIT_RATE, []) + t.get("cr_buf", 0) + cr_from_buff
        if "클레어(바니걸)" in cname: final_cr += p_stacks["claire_cr"] * 0.10
        if any(j.name == "깊은 애도" for j in jrs): final_cr += ra_cr_stack * 0.05
        
        final_cd = char.get_stat(StatType.CRIT_DAMAGE, []) + t.get("cd_buf", 0) + caster_cd_stack * 0.10
        if "아세라" in cname: final_cd += p_stacks["assera_cd"] * 0.06
        
        eff_cr = min(1.0, final_cr)
        eff_cd = final_cd
        
        # Jackpot logic removed (handled by JSON)
        # if is_frey and is_basic and frey_hr >= 5:
        #     frey_hr = 0
            
        dmg_raw = eff_atk * coeff * (1.0 + m_di) * (1.1) # 1.1 = Final generic multiplier
        
        # 4. Crit Calculation (OLD - to be replaced by final_cr/final_cd)
        cr_i = eff_cr
        cd_i = eff_cd
        
        omega_boost = (omega_dmg_stack * 0.05) if (is_spec or t.get("omega_elig", False)) else 0.0
        total_di = t.get("di", 0) + m_di + omega_boost + fx_carry
        if "샤를(바니걸)" in cname and is_ult:
            total_di += min(attr_stack * 0.05, 0.25)

        # Special Journey Logic (e.g., Chain Damage)
        chain_dmg = 0
        if cr_i > 0:
            if any(j.journey_type == "yumina_ex" for j in jrs):
                chain_dmg += eff_atk * 0.05 # Catalyst (Yumina)
            
        # Final Damage with Defense (v14.2)
        turn_dmg = (eff_atk * coeff * (1.0 + total_di + cr_i * cd_i) + chain_dmg) * def_multiplier
        
        # Rosaria Extra Basic (TN+)
        if rosaria_extra_basic:
            turn_dmg += (eff_atk * 1.50 * (1.0 + total_di + cr_i * cd_i)) * def_multiplier
        
        total_dmg += turn_dmg
        
        hits = t.get("hits", 4 if is_ult else 1)
        prob_crit_any = (1.0 - (1.0 - cr_i) ** hits)
        # ga_red_carry = 0.0 # REMOVED: This was overwriting JSON ag_boost!
        
        # FX Carry: Next turn DI +25% if Crit (Statistical: current_turn_cr * 0.25)
        if has_fx and t.get("coeff", 0) > 0:
            fx_carry = cr_i * 0.25
        elif t.get("coeff", 0) > 0:
            fx_carry = 0.0
            
        # EX Tracker
        if has_ex and is_basic:
            ex_basic_count += 1
            ex_total_cr += cr_i
        
        # AG Gain (Action Gauge) Tracking
        p_ga = cdata.get("패시브", {}).get("행동게이지_상수", 0)
        if (is_basic or t.get("is_extra_attack", False)) and p_ga > 0:
            ga_red_carry += p_ga
            
        if is_yumina:
            ga_red_carry += y_crit_ga * prob_crit_any
        if is_ult:
            if "로자리아" in cname: ga_red_carry += 0.50
            if "리디아" in cname: ga_red_carry += 0.30
            if "스마일" in cname: smile_def_red_turns = 2 # Apply 30% DEF Red for 2 turns
        
        # Buff/Debuff decrement
        smile_def_red_turns = max(0, smile_def_red_turns - 1)
        if t.get("note"):
            if "행게+30%" in t["note"]: ga_red_carry += 0.30
            if "행게+50%" in t["note"]: ga_red_carry += 0.50
        
        # Frey End-of-Turn & Ally Triggers
        if is_frey:
            if is_ult: frey_hr = min(frey_hr + 3, 5)
            if is_moon_party:
                ga_red_carry += 0.24 # 8% * 3 allies
                hr_chance = 0.5 if "1lv" in cname else 1.0
                frey_hr = min(frey_hr + 3 * hr_chance, 5)
            # Buff decrement (Every action consumes duration)
            frey_cr_turns = max(0, frey_cr_turns - 1)
            # Buff trigger (Special Skill sets duration to 3 for NEXT turns)
            if is_spec:
                frey_cr_turns = 3
        
        # Attribute Stack is now handle by pre-generator for most effects,
        # but we keep the state updates here for any remaining logic if needed.
        # (Though most should be in t.get('attribute_stack'))
        
        # 6. Post-Action stack updates
        is_crit = (np.random.rand() < eff_cr) # This is a statistical simulation, not a true random roll for a single run.
                                              # For average DPS, we assume average crit rate applies.
                                              # However, for conditional stacks like Blood Echo, we need a "crit" event.
                                              # For now, we'll use the effective crit rate as a probability.
        
        # 피의 메아리 Stack Update (v27.0 - 4 Target Assumption)
        TARGET_COUNT = 4
        if any(j.name == "피의 메아리" for j in jrs) and is_aoe and is_crit:
            rosa_atk_stack = min(5, rosa_atk_stack + TARGET_COUNT)
            
        # This `hits` list was likely intended for something else, but it's not used.
        # If it's meant to track individual hit damage for a more complex crit simulation,
        # it needs to be integrated differently. For average DPS, the `cr_i * cd_i` term
        # already accounts for average crit damage.
        # if is_crit:
        #     hits.append(dmg_raw * (1.0 + cd_i))


    return (total_dmg / cycle_time) if cycle_time > 0 else 0, total_dmg, cycle_time, total_dmg


def get_valid_journeys(char_name, char_class):
    valid = []
    for name, jr in JOURNEYS.items():
        # 🚨 "어느 한 기사의 맹세" 사용 안함 처리
        if name == "어느 한 기사의 맹세":
            continue
            
        rest = jr.restrict
        if not rest:
            valid.append(name)
            continue
        if "char" in rest and rest["char"] == char_name:
            valid.append(name)
            continue
        if "class" in rest and rest["class"] == char_class:
            valid.append(name)
            continue
    return valid

def find_best_journeys(char_name, char_class, cdata, rdata, eq_name, n=5, use_total_dmg=False, substat_vars=None):
    valid_names = get_valid_journeys(char_name, char_class)
    
    # Temporarily override EQUIPMENTS if substat_vars provided
    local_eqs = None
    if substat_vars:
        local_eqs = setup_equipments(substat_vars)
    specials = ["AX", "FX", "EX"]
    commons = [s for s in valid_names if s not in specials]
    
    combos = []
    if char_class == "어쌔신" and "키라만큼 귀여워" in valid_names:
        mandatory = "키라만큼 귀여워"
        others = [v for v in commons if v != mandatory]
        if len(others) >= n - 1:
            for combo in itertools.combinations(others, n - 1):
                combos.append([mandatory] + list(combo))
    elif len(commons) >= n:
        combos.extend(list(itertools.combinations(commons, n)))
    
    # SWEEP: Try both Standard and No-Ult configurations
    max_val_std, best_combo_std, best_bless_std = -1, [], None
    max_val_nu, best_combo_nu, best_bless_nu = -1, [], None
    
    available_blessings = [None] + [b for b in BLESSINGS.keys()]
    
    for b_name in available_blessings:
        for combo in combos:
            # Test Standard
            dps_s, total_s, _, _ = calculate_dps(char_name, cdata, rdata, eq_name, list(combo), b_name, 15, False, local_eqs)
            target_s = total_s if use_total_dmg else dps_s
            if target_s > max_val_std:
                max_val_std, best_combo_std, best_bless_std = target_s, list(combo), b_name
            
            # Test No-Ult
            dps_n, total_n, _, _ = calculate_dps(char_name, cdata, rdata, eq_name, list(combo), b_name, 15, True, local_eqs)
            target_n = total_n if use_total_dmg else dps_n
            if target_n > max_val_nu:
                max_val_nu, best_combo_nu, best_bless_nu = target_n, list(combo), b_name

    return {
        "standard": (best_combo_std, best_bless_std, max_val_std),
        "no_ult": (best_combo_nu, best_bless_nu, max_val_nu)
    }

def main():
    global EQUIPMENTS
    substat_vars = get_interactive_substats()
    EQUIPMENTS = setup_equipments(substat_vars)
    use_total_dmg = (substat_vars.get("METRIC", 2) == 2)

    # 2. Specs
    try:
        with open("Data/characters.json", "r", encoding="utf-8") as f:
            specs = json.load(f)
    except:
        specs = extract_json_from_md("Data/캐릭터_스펙_마스터.md")
        
    rotations = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    results = []
    
    metric_label = "Total Damage" if use_total_dmg else "DPS"
    print(f"\n[Star Savior Optimization Engine v14.0]")
    print(f" - Optimization Metric: {metric_label}")
    
    for cname, cdata in specs.items():
        if cname not in rotations: continue
        rdata = rotations[cname]
        char_class = cdata.get("분류", cdata.get("class", "Unknown"))
        if char_class == "디펜더": continue
        
        for eq_name in EQUIPMENTS.keys():
            # Meta-Sweep (Standard & No-Ult)
            best_stats = find_best_journeys(cname, char_class, cdata, rdata, eq_name, 5, use_total_dmg)
            
            # 1. Standard Rotation
            s_jrs, s_bless, s_val = best_stats["standard"]
            for t_limit in [5, 10, 15]:
                dps, _, _, _ = calculate_dps(cname, cdata, rotations[cname], eq_name, s_jrs, s_bless, t_limit, False)
                results.append({
                    "Character": cname, "Equip": eq_name, "Strategy": "Standard Rotation",
                    "Blessing": s_bless or "None", "Journeys": " | ".join(s_jrs), "Turns": t_limit, "DPS": round(dps, 2)
                })
            
            # 2. No-Ult Alternative
            n_jrs, n_bless, n_val = best_stats["no_ult"]
            for t_limit in [5, 10, 15]:
                dps, _, _, _ = calculate_dps(cname, cdata, rotations[cname], eq_name, n_jrs, n_bless, t_limit, True)
                results.append({
                    "Character": cname, "Equip": eq_name, "Strategy": "No-Ult AX Stacking",
                    "Blessing": n_bless or "None", "Journeys": " | ".join(n_jrs), "Turns": t_limit, "DPS": round(dps, 2)
                })
            
            print(f" > {cname} | {eq_name}: Standard {s_val:,.0f} / No-Ult {n_val:,.0f}")

    # Generate Top 3 Summary Report
    df = pd.DataFrame(results)
    df.to_csv("Results/dps_results.csv", index=False, encoding="utf-8-sig")
    
    with open("Results/optimization_guide.md", "w", encoding="utf-8") as f:
        f.write("# 스타 세이비어 캐릭터별 최적화 가이드 (Multi-Journey Edition)\n\n")
        f.write("> **업데이트 일시**: 2026-03-26\n")
        f.write("> **설명**: 5개의 여정 조합을 최우선으로 고려한 베스트 빌드 리포트입니다.\n\n")
        
        # 📋 구원자 목록 (Saviors List) 자동 생성
        f.write("### 📋 구원자 목록 (Saviors List)\n")
        char_list = df["Character"].unique()
        for i, label in enumerate(char_list):
            anchor = label.replace("(", "").replace(")", "").replace(",", "").replace(" ", "-").lower() 
            if i % 3 == 0: f.write("- ")
            f.write(f"[{label}](#{anchor})")
            if (i + 1) % 3 == 0: f.write("\n")
            elif i < len(char_list) - 1: f.write(" | ")
        if len(char_list) % 3 != 0: f.write("\n")
        f.write("\n---\n\n")
        
        for label in char_list:
            f.write(f"## {label}\n\n")
            char_df = df[df["Character"] == label]
            
            # ### 1. Standard Strategy section
            # 1. Standard Strategy (Ultimate Use)
            f.write("### 🔹 Standard Strategy (Ultimate Use)\n")
            f.write("> **공천**: 캐릭터 고유의 스킬 메커니즘을 100% 활용하는 권장 로테이션입니다.\n\n")
            
            std_all = char_df[(char_df["Strategy"] == "Standard Rotation") & (char_df["Turns"] == 15)].sort_values("DPS", ascending=False)
            
            # Identify Best 1 per 4-piece category
            categories = ["공격4", "통찰4", "파괴4", "체력4"]
            best_per_cat = {}
            for cat in categories:
                cat_df = std_all[std_all["Equip"].str.startswith(cat)].head(1)
                if not cat_df.empty:
                    best_per_cat[cat] = cat_df.iloc[0]
            
            f.write("| 순위 | 장비 세트 | 축복 | 최적 여정 조합 (Top 5) | DPS (15T) |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for i, row in enumerate(std_all.head(3).itertuples(), 1):
                f.write(f"| {i} | {row.Equip} | **{row.Blessing}** | {row.Journeys} | **{row.DPS:,.2f}** |\n")
            
            # Build Trajectory Analysis (v19.0)
            if not std_all.empty:
                f.write("\n#### 📈 빌드 진화 경로 (Optimal Build Trajectory)\n")
                f.write("> 부옵션 성장(0%~50%)에 따른 실시간 최적 조합 변화입니다.\n\n")
                
                cat_equip_names = [best_per_cat[c].Equip for c in categories if c in best_per_cat]
                
                for stype, label_ko in [(StatType.ATK, "공격력%"), (StatType.CRIT_DAMAGE, "치명타 피해"), (StatType.CRIT_RATE, "치명타 확률")]:
                    f.write(f"- **{label_ko}** 성장 경로:\n")
                    path = profile_stat_scaling(label, specs[label], rotations[label], cat_equip_names, stype, 0.5, 0.125, find_best_journeys)
                    
                    # Deduplicate and show transitions
                    last_point = None
                    for pt in path:
                        # ✅ 장비, 축복, 여정 조합 중 하나라도 바뀌면 출력 (여정 변화도 감지)
                        if not last_point or pt["equip"] != last_point["equip"] or pt["blessing"] != last_point["blessing"] or pt["journeys"] != last_point["journeys"]:
                            # ✅ DPS 수치 추가
                            f.write(f"  - **+{pt['increment']*100:4.1f}%**: {pt['equip']} ({pt['blessing']}) | **DPS: {pt['dps']:,.0f}** | {pt['journeys']}\n")
                            last_point = pt
                
                f.write("\n> (주어전) **표기 방식**: 증가량: 장비세트 (축복) | 주요 여정 리스트\n")

            # ### 2. No-Ult Strategy section
            f.write("\n### 🔸 Alternative: No-Ult Strategy (AX Stacking)\n")
            f.write("> **참고**: 궁극기를 포기하고 AX 스택 피해량에 올인한 특수 상황용 고점 빌드입니다.\n\n")
            nu_df = char_df[(char_df["Strategy"] == "No-Ult AX Stacking") & (char_df["Turns"] == 15)].sort_values("DPS", ascending=False).head(1)
            
            f.write("| 구분 | 장비 세트 | 축복 | 최적 여정 조합 (Top 5) | DPS (15T) |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for row in nu_df.itertuples():
                f.write(f"| **최고점** | {row.Equip} | **{row.Blessing}** | {row.Journeys} | **{row.DPS:,.2f}** |\n")
            
            f.write("\n---\n\n")

    print("\n[OK] Optimization Report generated in Results/optimization_guide.md")

if __name__ == "__main__":
    main()
