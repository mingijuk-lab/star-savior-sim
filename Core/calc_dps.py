import json
import re
import csv
import itertools

def extract_json_from_md(filepath):
    """Extracts all JSON blocks from a markdown file and merges them."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all ```json ... ``` blocks
    json_blocks = re.findall(r'```json\s+(.*?)\s+```', content, re.DOTALL)
    
    parsed_data = {}
    for block in json_blocks:
        try:
            # Pre-evaluate simple addition in JSON like 0.15+0.20
            block = re.sub(r'([0-9.]+)\+([0-9.]+)', lambda m: str(float(m.group(1)) + float(m.group(2))), block)
            
            if block.strip().startswith('"'):
                data = json.loads("{" + block + "}")
                parsed_data.update(data)
            else:
                data = json.loads(block)
                if "이름" in data:
                    parsed_data[data["이름"]] = data
                else:
                    parsed_data.update(data)
        except json.JSONDecodeError as e:
            # Skip invalid blocks or blocks that are just templates
            continue
    return parsed_data

# Define generic equipment sets
EQUIPMENTS = {
    "공격4세트": {"atk": 0.20, "cr": 0.0, "cd": 0.0, "spd": 0},
    "통찰4세트": {"atk": 0.00, "cr": 0.30, "cd": 0.0, "spd": 0},
    "파괴4세트": {"atk": 0.00, "cr": 0.0, "cd": 0.40, "spd": 0, "hp": 0.00},
    "속도4세트": {"atk": 0.00, "cr": 0.0, "cd": 0.0, "spd": 15, "hp": 0.00},
    "체력4세트": {"atk": 0.00, "cr": 0.0, "cd": 0.0, "spd": 0, "hp": 0.30},
}

# Define Arcana Stats
# assuming 레인저A is 14% atk, 30% cr (standard stats)
ARCANAS = {
    "어쌔신":     {"class": ["어쌔신"], "atk": 0.14, "cr": 0.30, "cd": 0.00, "type": "assassin"},
    "스트라이커A": {"class": ["스트라이커"], "atk": 0.14, "cr": 0.30, "cd": 0.00, "type": "strikerA"},
    "스트라이커B": {"class": ["스트라이커"], "atk": 0.14, "cr": 0.30, "cd": 0.00, "type": "strikerB"},
    "스트라이커C": {"class": ["스트라이커"], "atk": 0.14, "cr": 0.24, "cd": 0.12, "type": "strikerC"},
    "스트라이커D": {"class": ["스트라이커"], "atk": 0.06, "cr": 0.30, "cd": 0.12, "type": "strikerD"},
    "캐스터A":     {"class": ["캐스터"], "atk": 0.14, "cr": 0.30, "cd": 0.00, "type": "casterA"},
    "캐스터B":     {"class": ["캐스터"], "atk": 0.08, "cr": 0.30, "cd": 0.00, "type": "casterB"},
    "캐스터C":     {"class": ["캐스터"], "atk": 0.08, "cr": 0.24, "cd": 0.12, "type": "casterC"},
    "레인저A":     {"class": ["레인저"], "atk": 0.06, "cr": 0.24, "cd": 0.12, "type": "rangerA"},
    "레인저B":     {"class": ["레인저"], "atk": 0.06, "cr": 0.24, "cd": 0.12, "hp": 0.00, "type": "rangerB"},
    "레인저C":     {"class": ["레인저"], "atk": 0.06, "cr": 0.24, "cd": 0.00, "hp": 0.00, "type": "rangerC"},
    "레인저D":     {"class": ["레인저"], "atk": 0.00, "cr": 0.18, "cd": 0.12, "hp": 0.00, "type": "rangerD"},
    "디펜더A":     {"class": ["디펜더"], "atk": 0.00, "cr": 0.30, "cd": 0.00, "hp": 0.14, "type": "defenderA"},
}

JOURNEYS = {
    "AX": {"atk_base": 0.08, "cr": 0.0, "cd": 0.0, "type": "AX"},
    "FX": {"atk_base": 0.00, "cr": 0.0, "cd": 0.10, "type": "FX"},
    "EX": {"atk_base": 0.00, "cr": 0.10, "cd": 0.00, "type": "EX"},
}

def calculate_dps(cname, cdata, rdata, equip_name, arcana_name, journey_name):
    eq = EQUIPMENTS[equip_name]
    arc = ARCANAS[arcana_name]
    jr = JOURNEYS[journey_name]
    
    # Handle missing spec values safely
    base_atk = cdata.get("기본_스탯", {}).get("공격력", 0)
    base_hp = cdata.get("기본_스탯", {}).get("체력", 0)
    base_spd = cdata.get("기본_스탯", {}).get("속도", 100)
    base_cr = cdata.get("기본_스탯", {}).get("치명타_확률", 0.05)
    base_cd = cdata.get("기본_스탯", {}).get("치명타_피해", 0.50)
    
    res_pct = cdata.get("공명", {}).get("퍼센트", 0.0)
    if "공격력_퍼센트" in cdata.get("공명", {}): # Hilde format
        res_pct = cdata.get("공명", {}).get("공격력_퍼센트", 0.0)
    
    res_int = cdata.get("공명", {}).get("정수", 0.0)
    if "공격력_정수" in cdata.get("공명", {}): 
        res_int = cdata.get("공명", {}).get("공격력_정수", 0.0)

    pool = (base_atk + 1250) * (1 + res_pct) + res_int
    
    # Passives
    passive_atk = cdata.get("패시브", {}).get("공격력_퍼센트", 0.15)
    passive_cr = cdata.get("패시브", {}).get("치확_퍼센트", 0.0)
    lydia_stack = cdata.get("패시브", {}).get("lydia_stack", 0.0) # From JSON or 0

    arc_cd_stack = 0.0
    if arc["type"] in ["casterA", "casterB", "casterC"]:
        arc_cd_stack = 0.30 # 만스택 가정
        
    arc_spd_add = 0
    if arc["type"] == "assassin":
        arc_spd_add = 30
    elif arc["type"] == "strikerB":
        arc_spd_add = 8
        
    # Omega DMG (Striker A/C/D, Caster B/C, Ranger B)
    omega_max = 0.0
    if arc["type"] in ["strikerA", "strikerC", "casterB", "casterC", "rangerB"]:
        omega_max = 0.25  # +25%
    elif arc["type"] == "strikerD":
        omega_max = 0.30  # +30%
        
    d_static = passive_atk + lydia_stack + arc["atk"] + jr["atk_base"] + 0.01 + eq["atk"] + 0.1625
    final_spd = base_spd + 60 + arc_spd_add + eq["spd"]
    cr_base_total = min(base_cr + arc["cr"] + jr["cr"] + eq["cr"] + passive_cr, 1.0)
    cd_base_total = base_cd + arc["cd"] + arc_cd_stack + jr["cd"] + eq["cd"]
    
    # For simulation, run 2 cycles to reach steady state, and take the average of the 2nd cycle
    # Wait, the prompt says FX carry is from last cycle, Ranger A accumulates, Yumina accumulates.
    # To be accurate, we will simulate 50 turns (or loop the cycle enough times to hit 50 actions).
    
    MAX_ACTIONS = 10
    turns = rdata.get("turns", [])
    if not turns:
        return 0, 0, 0, 0
    cycle_time = 0.0
    total_dmg = 0.0
    
    # Stacks
    ax_stack = 0
    fx_carry = 0.0
    ga_reduction = 0.0 # Carryover from previous turn
    yumina_stack = 0
    frey_hr_stack = 0 # HR 스택 추적 추가
    lydia_stack = 0 # 리디아 스택 추적 추적
    
    # Rosaria specific stacks
    rosaria_upwa = 0.0
    rosaria_gukdong = 0
    
    ranger_a_cr_stack = 0
    ranger_a_atk_stack = 0.0
    ranger_c_spec_stack = 0
    ranger_c_atk_stack = 0.0
    ex_bonus_accum = 0.0
    ult_count_total = 0 # 리디아 궁극기 횟수 추적
    max_hit = 0.0 # 단일 히트 최대 데미지 추적 (기댓값 기준)

    action_idx = 0
    while action_idx < MAX_ACTIONS:
        for t in turns:
            if action_idx >= MAX_ACTIONS:
                break
            
            is_ult = t.get("is_ult", False)
            if is_ult: ult_count_total += 1
            
            action_idx += 1
            
            # Update Turn Start stacks
            if jr["type"] == "AX":
                ax_stack = min(ax_stack + 1, 5)

            # Determine hits (AoE 4 hits for Ult, else specified 'hits', default 1)
            base_hits = t.get("hits", 4 if is_ult else 1)
            
            # Action start settings
            spd_i = final_spd * t.get("spd_mult", 1.0)
            if spd_i > 0:
                turn_time = (1000.0 / spd_i) * (1.0 - ga_reduction)
                cycle_time += turn_time
            ga_reduction = 0.0 # Reset after use
            
            t_atk_buf = t.get("atk_buf", 0.0)
            t_di_buf = t.get("di", 0.0)
            t_cr_buf = t.get("cr_buf", 0.0)
            t_cd_buf = t.get("cd_buf", 0.0)
            
            turn_total_dmg = 0.0
            
            # Hit processing
            hit_list = []
            if t.get("coeff", 0.0) > 0:
                hit_coeff = t["coeff"] / base_hits
                hit_list.extend([hit_coeff] * base_hits)
            
            if t.get("extra_coeff", 0.0) > 0:
                hit_list.append(t["extra_coeff"])
            
            # For GA gain tracking/Crit tracking in this turn
            prob_none_crit = 1.0
            last_cr_i = 0.0
            total_expected_crit_hits = 0.0
            is_special = (not t.get("is_basic", False)) and (not is_ult) and t.get("coeff", 0) > 0

            # Rosaria Auto-Bonus Basic (if Upwa >= 3)
            if cname.startswith("로자리아") and is_special and rosaria_upwa >= 3.0:
                if t.get("extra_coeff", 0.0) == 0:
                    hit_list.append(1.50)

            for hit in hit_list:
                # Update stacks that might have changed from previous hit
                ranger_a_cr_bonus = (ranger_a_cr_stack * 0.05) if arc["type"] in ["rangerA", "rangerB", "rangerC", "rangerD"] else 0.0
                cr_i = min(cr_base_total + t_cr_buf + ranger_a_cr_bonus, 1.0)
                cd_i = cd_base_total + t_cd_buf
                crit_contrib = (cr_i * cd_i)
                last_cr_i = cr_i
                prob_none_crit *= (1.0 - cr_i)
                total_expected_crit_hits += cr_i
                
                ranger_a_atk_bonus = (ranger_a_atk_stack * 0.03) if arc["type"] == "rangerA" else 0.0
                ranger_c_atk_bonus = (ranger_c_atk_stack * 0.03) if arc["type"] in ["rangerC", "rangerD"] else 0.0
                dyn_atk = t_atk_buf + ranger_a_atk_bonus + ranger_c_atk_bonus
                
                if cname == "유미나":
                    dyn_atk += min(yumina_stack * 0.04, 0.20)
                if cname == "리디아":
                    dyn_atk += (lydia_stack * 0.06)

                ax_val = (ax_stack * 0.08) if jr["type"] == "AX" else 0.0
                eff_base = pool * (1 + d_static) + 1000
                eff_atk = eff_base * (1 + dyn_atk + ax_val)
                
                # DI calculation
                omega_di = omega_max if t.get("omega_elig", False) else 0.0
                ranger_c_spec_di = (ranger_c_spec_stack * 0.05) if arc["type"] in ["rangerC", "rangerD"] else 0.0
                
                # Rosaria Upwa DI logic (Applies to Special Skill)
                upwa_di_val = 0.0
                is_special = (not t.get("is_basic", False)) and (not is_ult) and t.get("coeff", 0) > 0
                if cname.startswith("로자리아") and is_special:
                    if rosaria_upwa >= 3.0: 
                        upwa_di_val = 0.40 # 20% + 20%
                    elif rosaria_upwa >= 2.0:
                        upwa_di_val = 0.20
                    elif rosaria_upwa >= 1.0:
                        upwa_di_val = 0.10
                        
                total_di = t_di_buf + omega_di + fx_carry + ranger_c_spec_di + upwa_di_val
                
                hit_dmg = (eff_atk * hit) * (1 + total_di + crit_contrib)
                turn_total_dmg += hit_dmg
                
                # On-Hit Side Effects
                if arc["type"] in ["rangerA", "rangerB", "rangerC", "rangerD"] and t.get("is_basic", False):
                    ranger_a_cr_stack = min(ranger_a_cr_stack + 1, 5)
                
                if is_ult:
                    if arc["type"] == "rangerA":
                        ranger_a_atk_stack = min(ranger_a_atk_stack + cr_i, 5.0)
                    if arc["type"] in ["rangerC", "rangerD"]:
                        ranger_c_atk_stack = min(ranger_c_atk_stack + cr_i, 5.0)
                
                if cname == "유미나":
                    yumina_stack = min(yumina_stack + 1, 5)
                    
                if cname.startswith("로자리아") and t.get("is_basic", False):
                    # Passive Upwa gain: Gukdong * 20%
                    rosaria_upwa = min(rosaria_upwa + (rosaria_gukdong * 0.20), 5.0)
            
            # Post-Action effects
            if cname == "유미나":
                yumina_ga_gain = cdata.get("패시브", {}).get("치명타_행게_증가", 0.0)
                ga_reduction = (1.0 - prob_none_crit) * yumina_ga_gain
            elif cname.startswith("프레이"):
                ga_reduction = 0.0
                if cname == "프레이(달속성파티)":
                    ga_reduction += 0.24 # 달속성 3인 공격
                if "강제협상" in t.get("note", ""):
                    ga_reduction += 0.30 # HR 5스택 소모 시 30% 증가
                if "추가턴" in t.get("note", "") and t.get("coeff", 1.0) == 0.0:
                    ga_reduction += 1.0 # 100% 증가 (즉시 추가턴)
            else:
                ga_reduction = 0.0 # Standard reset or overridden by Lydia Ult below
            
            if cname.startswith("로자리아"):
                if is_ult:
                    # Prob Success = 1 - None Crit
                    prob_success = 1.0 - prob_none_crit
                    # Expected growth = prob * (min(expected_crit_hits, 3))
                    growth = prob_success * min(total_expected_crit_hits, 3.0)
                    # If fail, reset
                    rosaria_upwa = prob_success * (rosaria_upwa + growth)
                    rosaria_gukdong = min(rosaria_gukdong + 1, 5)
                elif is_special:
                    rosaria_upwa = 0 # Consume
                    rosaria_gukdong = min(rosaria_gukdong + 1, 5)
                elif t.get("is_basic", False):
                    rosaria_gukdong = min(rosaria_gukdong + 1, 5)

            if t.get("is_basic", False) and cname == "리디아":
                lydia_stack = min(lydia_stack + 1, 5)
                
            if jr["type"] == "FX" and len(hit_list) > 0:
                fx_carry = last_cr_i * 0.25
                
            if jr["type"] == "EX" and t.get("is_basic", False):
                ex_bonus_accum += last_cr_i * 0.25 * 16215
            
            is_special = (not t.get("is_basic", False)) and (not is_ult) and t.get("coeff", 0) > 0
            if is_special and arc["type"] in ["rangerB", "rangerC", "rangerD"]:
                ranger_c_spec_stack = min(ranger_c_spec_stack + 1, 5)

            if is_ult:
                if jr["type"] == "AX":
                    ax_stack = 0
                if cname == "리디아":
                    ga_reduction = 0.30

            total_dmg += turn_total_dmg
            if turn_total_dmg > max_hit:
                max_hit = turn_total_dmg
        # End of turn loop
    
    # Final tally
    total_dmg += ex_bonus_accum
    
    if cycle_time == 0: return 0,0,0,0
    
    dps = total_dmg / cycle_time
    
    return dps, total_dmg, cycle_time, max_hit

def main():
    specs = extract_json_from_md("d:/Star/Data/캐릭터_스펙_마스터.md")
    rotations = extract_json_from_md("d:/Star/Data/사이클_로테이션_마스터.md")
    
    # Some chars might only exist in specs, skip if no rotation
    results = []
    
    for cname, cdata in specs.items():
        print(f"Processing candidate: {cname}")
        if cname not in rotations:
            continue
        print(f"Starting simulation for: {cname}")
        rdata = rotations[cname]
        cclass = cdata.get("분류", "일반")
        
        for eq_name in EQUIPMENTS.keys():
            for arc_name, arc_data in ARCANAS.items():
                # Check class compatibility: 분류와 아르카나 class 배열 직접 매칭
                valid = cclass in arc_data["class"]

                if not valid:
                    continue
                        
                for jr_name in JOURNEYS.keys():
                    dps, total, time, max_hit = calculate_dps(cname, cdata, rdata, eq_name, arc_name, jr_name)
                    results.append({
                        "Character": cname,
                        "Class": cclass,
                        "Equip": eq_name,
                        "Arcana": arc_name,
                        "Journey": jr_name,
                        "DPS": round(dps, 2),
                        "MaxHit": round(max_hit, 2)
                    })
    
    # Sort and save
    results.sort(key=lambda x: (x["Character"], -x["DPS"]))
    
    with open("d:/Star/Results/dps_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["Character", "Class", "Equip", "Arcana", "Journey", "DPS", "MaxHit"])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Computed {len(results)} combinations. Saved to dps_results.csv.")

if __name__ == "__main__":
    main()
