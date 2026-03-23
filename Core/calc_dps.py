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

class Mechanic:
    def __init__(self, cname, cdata):
        self.cname = cname
        self.cdata = cdata
        self.stacks = {}
        self.ga_gain = 0.0
    def hit_pre(self, t, arc): return 0.0, 0.0 # di_bonus, atk_bonus
    def on_hit(self, t, is_ult, cr_i): pass
    def post_action(self, t, is_ult, prob_none_crit, total_expected_crit_hits): return 0.0 # ga_reduction

class FreyMechanic(Mechanic):
    def __init__(self, cname, cdata):
        super().__init__(cname, cdata)
        self.stacks = {"hr": 0.0, "cooling": 0}
    def hit_pre(self, t, arc):
        di = self.stacks["hr"] * 0.01
        if "강제협상" in t.get("note", "") and t.get("di", 0.0) < 0.5: di += 1.00
        return di, 0.0
    def on_hit(self, t, is_ult, cr_i):
        is_spec = "특수기" in t.get("note", "") or t.get("omega_elig", False)
        if t.get("is_basic", False): self.stacks["cooling"] += 1
        elif is_spec: self.stacks["cooling"] += 3
        if self.stacks["cooling"] >= 5:
            self.stacks["hr"] = min(self.stacks["hr"] + 1, 5)
            self.stacks["cooling"] = 0
    def post_action(self, t, is_ult, prob_none_crit, total_expected_crit_hits):
        ga = 0.0
        if self.cname == "프레이(달속성파티)":
            ga += 0.24
            hr_p = self.cdata.get("패시브", {}).get("hr_확률", 1.0)
            self.stacks["hr"] = min(self.stacks["hr"] + (3 * hr_p), 5.0)
        if "강제협상" in t.get("note", ""):
            ga += 0.30
            self.stacks["hr"] = 0
        if "추가턴" in t.get("note", "") and t.get("coeff", 1.0) == 0.0: ga += 1.0
        if is_ult: self.stacks["hr"] = min(self.stacks["hr"] + 3, 5)
        return ga

class RosariaMechanic(Mechanic):
    def __init__(self, cname, cdata):
        super().__init__(cname, cdata)
        self.stacks = {"upwa": 0.0, "gukdong": 0}
    def hit_pre(self, t, arc):
        is_spec = (not t.get("is_basic", False)) and (not t.get("is_ult", False)) and t.get("coeff", 0) > 0
        di = 0.0
        if is_spec:
            if self.stacks["upwa"] >= 3.0: di = 0.40
            elif self.stacks["upwa"] >= 2.0: di = 0.20
            elif self.stacks["upwa"] >= 1.0: di = 0.10
        return di, 0.0
    def on_hit(self, t, is_ult, cr_i):
        if t.get("is_basic", False):
            self.stacks["upwa"] = min(self.stacks["upwa"] + (self.stacks["gukdong"] * 0.20), 5.0)
    def post_action(self, t, is_ult, prob_none_crit, total_expected_crit_hits):
        is_spec = (not t.get("is_basic", False)) and (not t.get("is_ult", False)) and t.get("coeff", 0) > 0
        if is_ult:
            p_s = 1.0 - prob_none_crit
            growth = p_s * min(total_expected_crit_hits, 3.0)
            self.stacks["upwa"] = p_s * (self.stacks["upwa"] + growth)
            self.stacks["gukdong"] = min(self.stacks["gukdong"] + 1, 5)
        elif is_spec:
            self.stacks["upwa"] = 0
            self.stacks["gukdong"] = min(self.stacks["gukdong"] + 1, 5)
        else:
            self.stacks["gukdong"] = min(self.stacks["gukdong"] + 1, 5)
        return 0.0

class LydiaMechanic(Mechanic):
    def __init__(self, cname, cdata):
        super().__init__(cname, cdata)
        self.lydia_stack = 0
    def hit_pre(self, t, arc):
        return 0.0, self.lydia_stack * 0.06
    def on_hit(self, t, is_ult, cr_i):
        if t.get("is_basic", False): self.lydia_stack = min(self.lydia_stack + 1, 5)
    def post_action(self, t, is_ult, prob_none_crit, total_expected_crit_hits):
        return 0.30 if is_ult else 0.0

class YuminaMechanic(Mechanic):
    def __init__(self, cname, cdata):
        super().__init__(cname, cdata)
        self.yumina_stack = 0
    def hit_pre(self, t, arc):
        return 0.0, min(self.yumina_stack * 0.04, 0.20)
    def on_hit(self, t, is_ult, cr_i):
        self.yumina_stack = min(self.yumina_stack + 1, 5)
    def post_action(self, t, is_ult, prob_none_crit, total_expected_crit_hits):
        gain = self.cdata.get("패시브", {}).get("치명타_행게_증가", 0.0)
        return (1.0 - prob_none_crit) * gain

def get_mechanic(cname, cdata):
    if cname.startswith("프레이"): return FreyMechanic(cname, cdata)
    if cname.startswith("로자리아"): return RosariaMechanic(cname, cdata)
    if cname == "리디아": return LydiaMechanic(cname, cdata)
    if cname == "유미나": return YuminaMechanic(cname, cdata)
    return Mechanic(cname, cdata)

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
    
    # Stacks and Mechanic
    m = get_mechanic(cname, cdata)
    ax_stack = 0
    fx_carry = 0.0
    ga_reduction = 0.0
    
    ranger_a_cr_stack = 0
    ranger_a_atk_stack = 0.0
    ranger_c_spec_stack = 0
    ranger_c_atk_stack = 0.0
    ex_bonus_accum = 0.0
    max_hit = 0.0

    action_idx = 0
    while action_idx < MAX_ACTIONS:
        for t in turns:
            if action_idx >= MAX_ACTIONS: break
            
            is_ult = t.get("is_ult", False)
            action_idx += 1
            
            if jr["type"] == "AX": ax_stack = min(ax_stack + 1, 5)

            base_hits = t.get("hits", 4 if is_ult else 1)
            spd_i = final_spd * t.get("spd_mult", 1.0)
            if spd_i > 0:
                turn_time = (1000.0 / spd_i) * (1.0 - ga_reduction)
                cycle_time += turn_time
            ga_reduction = 0.0
            
            t_atk_buf = t.get("atk_buf", 0.0)
            t_di_buf = t.get("di", 0.0)
            t_cr_buf = t.get("cr_buf", 0.0)
            t_cd_buf = t.get("cd_buf", 0.0)
            
            turn_total_dmg = 0.0
            
            hit_list = []
            if t.get("coeff", 0.0) > 0:
                hit_coeff = t["coeff"] / base_hits
                hit_list.extend([hit_coeff] * base_hits)
            
            if t.get("extra_coeff", 0.0) > 0:
                hit_list.append(t["extra_coeff"])
            
            # Rosaria Auto-Bonus Basic
            is_spec = (not t.get("is_basic", False)) and (not is_ult) and t.get("coeff", 0) > 0
            if cname.startswith("로자리아") and is_spec and m.stacks["upwa"] >= 3.0:
                if t.get("extra_coeff", 0.0) == 0: hit_list.append(1.50)

            prob_none_crit = 1.0
            total_expected_crit_hits = 0.0

            for hit in hit_list:
                m_di, m_atk = m.hit_pre(t, arc)
                
                ra_cr = (ranger_a_cr_stack * 0.05) if arc["type"] in ["rangerA", "rangerB", "rangerC", "rangerD"] else 0.0
                cr_i = min(cr_base_total + t_cr_buf + ra_cr, 1.0)
                cd_i = cd_base_total + t_cd_buf
                crit_contrib = (cr_i * cd_i)
                prob_none_crit *= (1.0 - cr_i)
                total_expected_crit_hits += cr_i
                
                ra_atk = (ranger_a_atk_stack * 0.03) if arc["type"] == "rangerA" else 0.0
                rc_atk = (ranger_c_atk_stack * 0.03) if arc["type"] in ["rangerC", "rangerD"] else 0.0
                dyn_atk = t_atk_buf + ra_atk + rc_atk + m_atk
                
                ax_val = (ax_stack * 0.08) if jr["type"] == "AX" else 0.0
                eff_base = pool * (1 + d_static) + 1000
                eff_atk = eff_base * (1 + dyn_atk + ax_val)
                
                omega_di = omega_max if t.get("omega_elig", False) else 0.0
                rc_spec_di = (ranger_c_spec_stack * 0.05) if arc["type"] in ["rangerC", "rangerD"] else 0.0
                
                total_di = t_di_buf + omega_di + fx_carry + rc_spec_di + m_di
                
                hit_dmg = (eff_atk * hit) * (1 + total_di + crit_contrib)
                turn_total_dmg += hit_dmg
                
                # On-Hit
                if arc["type"] in ["rangerA", "rangerB", "rangerC", "rangerD"] and t.get("is_basic", False):
                    ranger_a_cr_stack = min(ranger_a_cr_stack + 1, 5)
                
                if is_ult:
                    if arc["type"] == "rangerA": ranger_a_atk_stack = min(ranger_a_atk_stack + cr_i, 5.0)
                    if arc["type"] in ["rangerC", "rangerD"]: ranger_c_atk_stack = min(ranger_c_atk_stack + cr_i, 5.0)
                
                m.on_hit(t, is_ult, cr_i)
            
            # Post-Action
            ga_reduction = m.post_action(t, is_ult, prob_none_crit, total_expected_crit_hits)
            
            if jr["type"] == "FX" and len(hit_list) > 0:
                fx_carry = (1.0 - prob_none_crit) * 0.25

            if jr["type"] == "EX" and t.get("is_basic", False):
                ex_bonus_accum += (1.0 - prob_none_crit) * 0.25 * 16215
            
            is_spec = (not t.get("is_basic", False)) and (not is_ult) and t.get("coeff", 0) > 0
            if is_spec and arc["type"] in ["rangerB", "rangerC", "rangerD"]:
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
    specs = extract_json_from_md("Data/캐릭터_스펙_마스터.md")
    rotations = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    
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
    
    with open("Results/dps_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["Character", "Class", "Equip", "Arcana", "Journey", "DPS", "MaxHit"])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Computed {len(results)} combinations. Saved to dps_results.csv.")

if __name__ == "__main__":
    main()
