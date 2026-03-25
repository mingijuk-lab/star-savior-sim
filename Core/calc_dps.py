import json
import re
import csv
import itertools
import sys
import pandas as pd
from Core.models import StatType, Modifier, ModifierType, EquipmentPiece, EquipmentSet, Arcana, Journey, Character
from Core.data_loader import extract_json_from_md, load_equipments_from_json

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

def calculate_dps(cname, cdata, rdata, eq_name, jr_names, blessing_name=None, max_actions=15, force_no_ult=False):
    """
    jr_names: List of journey names (up to 5).
    """
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
    
    total_dmg, cycle_time, ga_red_carry, omega_dmg_stack, assassin_spd_stack, caster_cd_stack, ra_cr_stack = 0.0, 0.0, 0.0, 0, 0, 0, 0
    fx_carry = 0.0
    ex_basic_count = 0
    ex_total_cr = 0.0
    frey_hr = 0
    frey_cr_turns = 0
    bleeding_dots = []
    
    # Universal Attribute (속성) Stack
    attr_stack = 0
    # Rosaria Ignition (업화)
    is_rosaria = "로자리아" in cname
    ros_ign_stack = 0

    action_idx = 0
    for t in rdata["turns"]:
        if action_idx >= max_actions:
            break
            
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
        
        # Frey Dynamic Mechanics
        is_frey = "프레이" in cname
        is_moon_party = "달속성파티" in cname
        is_jackpot = False
        if is_frey and is_basic and frey_hr >= 5:
            is_jackpot = True
            m_di += 1.00 + (frey_hr * 0.01) # 100% Fixed + Stack Bonus
            frey_hr = 0
            # AG +30% handled later
            
        # Yumina State Detection
        is_yumina = "유미나" in cname
        y_is_1lv = "1lv" in cname
        y_atk_per_stack = 0.02 if y_is_1lv else 0.04
        y_crit_ga = 0.09 if y_is_1lv else 0.15
        
        # Buff Application (Starts after Spec, so if it was set in PREVIOUS end-of-turn, it's active now)
        cr_from_buff = 0.30 if (is_frey and frey_cr_turns > 0) else 0.0
            
        # Stacking logic for specialized Journeys
        if any(j.name == "키라만큼 귀여워" for j in jrs): assassin_spd_stack = min(assassin_spd_stack + 1, 3)
        if any(j.name == "하늘의 심판" for j in jrs): caster_cd_stack = min(caster_cd_stack + 1, 3)
        if any(j.name == "깊은 애도" for j in jrs) and (is_basic or t.get("extra_coeff", 0) > 0):
            ra_cr_stack = min(ra_cr_stack + 1, 5)

        dyn_mods = []
        if assassin_spd_stack > 0: dyn_mods.append(Modifier(StatType.SPEED, assassin_spd_stack * 10, ModifierType.FLAT, "AssassinStack"))
        
        final_spd = char.get_stat(StatType.SPEED, dyn_mods) * t.get("spd_mult", 1.0)
        
        # Extra Attack (TN+) Logic: If marked as extra_attack, this action consumes no time.
        if not t.get("is_extra_attack", False):
            turn_time = (1000.0 / final_spd) * (1.0 - ga_red_carry)
            cycle_time += turn_time
            ga_red_carry = 0.0 # Consume carry
            
        # Register next AG reduction if applicable (Standard style only)
        if not force_no_ult:
            ga_red_carry = t.get("ag_boost", 0.0)
            if is_jackpot: ga_red_carry = 0.30
        
        if any(j.name == "허수의 개척자" for j in jrs):
            if is_spec: omega_dmg_stack = min(omega_dmg_stack + 1, 5)

        m_di, m_atk_mult, coeff = 0.0, 1.0, t.get("coeff", 0) + t.get("extra_coeff", 0)
        
        # Apply Attribute (속성) Dynamic Stats
        if is_yumina:
            m_atk_mult *= (1.0 + t.get("yumina_hit_stack", 0) * y_atk_per_stack)
            # Yumina's Leap (attr_stack) threshold for DI removed as it is not in spec. 
            # Leap is used below for Bleed count logic.

        for k, v in t.items():
            if k.endswith("_di"): m_di += v
            if k.endswith("_atk_p"): m_atk_mult *= (1.0 + v)
            if k.startswith("lydia_stack"): m_atk_mult *= (1.0 + v * 0.06)
            # yumina_stack/doyak from JSON are now ignored in favor of dynamic engine
        
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
        
        # 3. Dynamic ATK and Multipliers
        # AX Formula: eff_atk = [pool * (1 + d_static) + 1000] * (1 + AX_stack * 0.08 + atk_buf)
        res_p = res.get("퍼센트", 0)
        res_flat = res.get("정수", 0)
        resonance_val = (raw_pool * res_p + res_flat)
        
        if has_ax:
            eff_atk = eff_base * (1.0 + ax_stacks[action_idx] * 0.08 + t.get("atk_buf", 0)) * m_atk_mult + resonance_val
        else:
            # Non-AX: (1 + static + dynamic)
            eff_atk = (raw_pool * (1.0 + static_atk_p + t.get("atk_buf", 0)) + 1000) * m_atk_mult + resonance_val
        
        # 4. Crit Calculation
        cr_dyn = ra_cr_stack * 0.05 + t.get("cr_buf", 0) + cr_from_buff
        if action_idx < 2 and any(j.name == "친구들과의 산책" for j in jrs):
            cr_dyn += 0.30
        cd_dyn = caster_cd_stack * 0.10 + t.get("cd_buf", 0)
        
        cr_i = min(char.get_stat(StatType.CRIT_RATE, [Modifier(StatType.CRIT_RATE, cr_dyn)]) + res.get("치확_퍼센트", 0), 1.0)
        cd_i = char.get_stat(StatType.CRIT_DAMAGE, [Modifier(StatType.CRIT_DAMAGE, cd_dyn)])
        
        omega_boost = (omega_dmg_stack * 0.05) if (is_spec or t.get("omega_elig", False)) else 0.0
        total_di = t.get("di", 0) + m_di + omega_boost + fx_carry
        if "샤를(바니걸)" in cname and is_ult:
            total_di += min(attr_stack * 0.05, 0.25)

        # Special Journey Logic (e.g., Chain Damage)
        chain_dmg = 0
        if cr_i > 0:
            if any(j.journey_type == "yumina_ex" for j in jrs):
                chain_dmg += eff_atk * 0.05 # Catalyst (Yumina)
            
        turn_dmg = eff_atk * coeff * (1.0 + total_di + cr_i * cd_i) + chain_dmg
        
        # Rosaria Extra Basic (TN+)
        if rosaria_extra_basic:
            turn_dmg += eff_atk * 1.50 * (1.0 + total_di + cr_i * cd_i)
        
        total_dmg += turn_dmg
        
        hits = t.get("hits", 4 if is_ult else 1)
        prob_crit_any = (1.0 - (1.0 - cr_i) ** hits)
        ga_red_carry = 0.0
        
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
        if t.get("note"):
            if "행게+30%" in t["note"]: ga_red_carry += 0.30
            if "행게+50%" in t["note"]: ga_red_carry += 0.50
        
        # Frey End-of-Turn & Ally Triggers
        if is_frey:
            if is_jackpot: ga_red_carry += 0.30
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
        
        action_idx += 1

    # Apply EX Bonus (v6): basic_count * cr_i * 0.25 * 16215
    if has_ex and ex_basic_count > 0:
        avg_cr = ex_total_cr / ex_basic_count
        ex_bonus = ex_basic_count * avg_cr * 0.25 * 16215
        total_dmg += ex_bonus

    return (total_dmg / cycle_time) if cycle_time > 0 else 0, total_dmg, cycle_time, total_dmg

def solve_cd_threshold(cdata, char_name, char_class, jrs):
    """Calculates the specific Crit Damage threshold for Insight 4set vs Attack 4set using v6 Engine Logic."""
    # Build a temporary Character to get accurate Pool and Static ATK
    res = cdata.get("공명", {})
    raw_pool = (cdata["기본_스탯"]["공격력"] + 1250)
    
    # Static ATK% (Passive + Journey + Substats)
    sa = cdata.get("패시브", {}).get("공격력_퍼센트", 0) + 0.1625 + 0.01
    for jr in jrs:
        for mod in jr.modifiers:
            if mod.stat_type == StatType.ATK and mod.mod_type == ModifierType.PERCENT:
                sa += mod.value
    
    # eff_base (Stella + Static + System)
    eff_base = raw_pool * (1.0 + sa) + 1000
    
    # AX Multiplier (Average 15-turn stack estimate: ~3.0 for Rosaria, ~2.0 for others)
    has_ax = any(jr.journey_type == "AX" for jr in jrs)
    ax_mult = (1.0 + 3.0 * 0.08) if has_ax else 1.0 
    
    # ATK Gain from Attack Set (20%)
    # In AX: it multiplies the whole eff_base
    # In Non-AX: it's additive to sa
    if has_ax:
        Atk4_gain = eff_base * 0.20 * ax_mult
    else:
        Atk4_gain = raw_pool * 0.20
    
    # Effective Base Damage (Before Crit)
    B = eff_base * ax_mult
    
    # Crit Rate
    Cr_base = cdata["기본_스탯"]["치명타_확률"] + res.get("치확_퍼센트", 0)
    for jr in jrs:
        for mod in jr.modifiers:
            if mod.stat_type == StatType.CRIT_RATE:
                Cr_base += mod.value
    
    Cr_atk4 = min(1.0, Cr_base)
    Cr_ins4 = min(1.0, Cr_base + 0.30)
    
    if Cr_ins4 <= Cr_atk4: return 999.9
    
    # Solve: (B + Atk4_gain) * (1 + Cr_atk4 * CD) = B * (1 + Cr_ins4 * CD)
    # (B + G) + (B*Cr_a + G*Cr_a)*CD = B + B*Cr_i*CD
    # G = [B*Cr_i - (B*Cr_a + G*Cr_a)] * CD
    # CD = G / (B*(Cr_i - Cr_a) - G*Cr_a)
    
    denom = B * (Cr_ins4 - Cr_atk4) - Atk4_gain * Cr_atk4
    if denom <= 0: return 999.9
    
    CD_needed = Atk4_gain / denom
    
    # Current CD
    current_cd = cdata["기본_스탯"]["치명타_피해"]
    for jr in jrs:
        for mod in jr.modifiers:
            if mod.stat_type == StatType.CRIT_DAMAGE:
                current_cd += mod.value
                
    return max(0, CD_needed - current_cd)

def get_valid_journeys(char_name, char_class):
    valid = []
    for name, jr in JOURNEYS.items():
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

def find_best_journeys(char_name, char_class, cdata, rdata, eq_name, n=5, use_total_dmg=False):
    valid_names = get_valid_journeys(char_name, char_class)
    
    # Journeys are purely common now
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
            dps_s, total_s, _, _ = calculate_dps(char_name, cdata, rdata, eq_name, list(combo), b_name, 15, False)
            target_s = total_s if use_total_dmg else dps_s
            if target_s > max_val_std:
                max_val_std, best_combo_std, best_bless_std = target_s, list(combo), b_name
            
            # Test No-Ult
            dps_n, total_n, _, _ = calculate_dps(char_name, cdata, rdata, eq_name, list(combo), b_name, 15, True)
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

    specs, rotations = extract_json_from_md("Data/캐릭터_스펙_마스터.md"), extract_json_from_md("Data/사이클_로테이션_마스터.md")
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
        f.write("> **업데이트 일시**: 2026-03-25\n")
        f.write("> **설명**: 5개의 여정 조합을 최우선으로 고려한 베스트 빌드 리포트입니다.\n\n")
        
        for label in df["Character"].unique():
            f.write(f"## {label}\n\n")
            char_df = df[df["Character"] == label]
            
            # ### 1. Standard Strategy section
            f.write("### 🔹 Standard Strategy (Ultimate Use)\n")
            f.write("> **공천**: 캐릭터 고유의 스킬 메커니즘을 100% 활용하는 권장 로테이션입니다.\n\n")
            std_df = char_df[(char_df["Strategy"] == "Standard Rotation") & (char_df["Turns"] == 15)].sort_values("DPS", ascending=False).head(3)
            
            f.write("| 순위 | 장비 세트 | 축복 | 최적 여정 조합 (Top 5) | DPS (15T) |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for i, row in enumerate(std_df.itertuples(), 1):
                f.write(f"| {i} | {row.Equip} | **{row.Blessing}** | {row.Journeys} | **{row.DPS:,.2f}** |\n")
            
            # Threshold Analysis (Linked to Top 1 Standard)
            if not std_df.empty:
                top1_s = std_df.iloc[0]
                jrs_obj = [JOURNEYS[j] for j in top1_s.Journeys.split(" | ")]
                if top1_s.Blessing != "None": jrs_obj.append(BLESSINGS[top1_s.Blessing])
                cd_threshold = solve_cd_threshold(specs[label], label, specs[label].get("분류", "Unknown"), jrs_obj)
                
                f.write("\n#### ⚖️ Standard 세팅 임계점 (Threshold Analysis)\n")
                if cd_threshold > 9.0: f.write("- **통찰 4세트 교체**: 공격 세트 대비 효율 저하로 권장하지 않음.\n")
                else: f.write(f"- **통찰 4세트 교체**: 공격 세트 대비 치명타 피해 부옵션 **+{cd_threshold:7.1%}** 이상 시 권장.\n")

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
