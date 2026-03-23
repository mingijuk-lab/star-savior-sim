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
# 대부분 24%가 기본, 레인저만 특수 기믹 (기본기 타격 시 치확+5%, 최대 5회)
ARCANAS = {
    "어쌔신":     {"class": ["어쌔신"], "atk": 0.14, "cr": 0.30, "cd": 0.00, "type": "assassin"},
    "스트라이커A": {"class": ["스트라이커", "디펜더"], "atk": 0.14, "cr": 0.30, "cd": 0.00, "type": "strikerA"},
    "스트라이커B": {"class": ["스트라이커", "디펜더"], "atk": 0.14, "cr": 0.30, "cd": 0.00, "type": "strikerB"},
    "스트라이커C": {"class": ["스트라이커", "디펜더"], "atk": 0.14, "cr": 0.24, "cd": 0.12, "type": "strikerC"},
    "스트라이커D": {"class": ["스트라이커", "디펜더"], "atk": 0.06, "cr": 0.30, "cd": 0.12, "type": "strikerD"},
    "캐스터A":     {"class": ["캐스터"], "atk": 0.14, "cr": 0.30, "cd": 0.00, "type": "casterA"},
    "캐스터B":     {"class": ["캐스터"], "atk": 0.08, "cr": 0.30, "cd": 0.00, "type": "casterB"},
    "캐스터C":     {"class": ["캐스터"], "atk": 0.08, "cr": 0.24, "cd": 0.12, "type": "casterC"},
    "레인저A":     {"class": ["레인저"], "atk": 0.06, "cr": 0.24, "cd": 0.12, "type": "rangerA"},
    "레인저B":     {"class": ["레인저"], "atk": 0.06, "cr": 0.24, "cd": 0.12, "type": "rangerB"},
    "레인저C":     {"class": ["레인저"], "atk": 0.06, "cr": 0.24, "cd": 0.00, "type": "rangerC"},
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
    def get_spd_mult(self): return 0.0 # additional spd multiplier

class FreyMechanic(Mechanic):
    def __init__(self, cname, cdata):
        super().__init__(cname, cdata)
        self.stacks = {"hr": 0.0, "cooling": 0}
        self.ult_atk_timer = 0
    def hit_pre(self, t, arc):
        di = self.stacks["hr"] * 0.01
        if "강제협상" in t.get("note", "") and t.get("di", 0.0) < 0.5: di += 1.00
        atk = 0.30 if self.ult_atk_timer > 0 else 0.0
        return di, atk
    def on_hit(self, t, is_ult, cr_i):
        is_spec = "특수기" in t.get("note", "") or t.get("omega_elig", False)
        if t.get("is_basic", False): self.stacks["cooling"] += 1
        elif is_spec: self.stacks["cooling"] += 3
        if self.stacks["cooling"] >= 5:
            self.stacks["hr"] = min(self.stacks["hr"] + 1, 5)
            self.stacks["cooling"] = 0
    def post_action(self, t, is_ult, prob_none_crit, total_expected_crit_hits):
        if self.ult_atk_timer > 0: self.ult_atk_timer -= 1
        ga = 0.0
        if self.cname == "프레이(달속성파티)":
            ga += 0.24
            hr_p = self.cdata.get("패시브", {}).get("hr_확률", 1.0)
            self.stacks["hr"] = min(self.stacks["hr"] + (3 * hr_p), 5.0)
        if "강제협상" in t.get("note", ""):
            ga += 0.30
            self.stacks["hr"] = 0
        if "추가턴" in t.get("note", "") and t.get("coeff", 1.0) == 0.0: ga += 1.0
        if is_ult:
            self.stacks["hr"] = min(self.stacks["hr"] + 3, 5)
            self.ult_atk_timer = 2
        return ga

class RosariaMechanic(Mechanic):
    def __init__(self, cname, cdata):
        super().__init__(cname, cdata)
        self.stacks = {"upwa": 0.0, "gukdong": 0}
        self.master_timer = 0 # 옥좌의 주인
    def hit_pre(self, t, arc):
        is_spec = (not t.get("is_basic", False)) and (not t.get("is_ult", False)) and t.get("coeff", 0) > 0
        di = 0.0
        if is_spec:
            if self.stacks["upwa"] >= 3.0: di += 0.40
            elif self.stacks["upwa"] >= 2.0: di += 0.20
            elif self.stacks["upwa"] >= 1.0: di += 0.10
        if self.master_timer > 0 and t.get("is_basic", False):
            di += 0.15 # 옥좌의 주인 기본기 피증
        return di, 0.0
    def on_hit(self, t, is_ult, cr_i):
        if t.get("is_basic", False):
            self.stacks["upwa"] = min(self.stacks["upwa"] + (self.stacks["gukdong"] * 0.20), 5.0)
    def post_action(self, t, is_ult, prob_none_crit, total_expected_crit_hits):
        if self.master_timer > 0: self.master_timer -= 1
        is_spec = (not t.get("is_basic", False)) and (not t.get("is_ult", False)) and t.get("coeff", 0) > 0
        if is_ult:
            p_s = 1.0 - prob_none_crit
            growth = p_s * min(total_expected_crit_hits, 3.0)
            self.stacks["upwa"] = p_s * (self.stacks["upwa"] + growth)
            self.stacks["gukdong"] = min(self.stacks["gukdong"] + 1, 5)
            self.master_timer = 3
        elif is_spec:
            self.stacks["upwa"] = 0
            self.stacks["gukdong"] = min(self.stacks["gukdong"] + 1, 5)
        else:
            self.stacks["gukdong"] = min(self.stacks["gukdong"] + 1, 5)
        return 0.0
    def get_spd_mult(self):
        return 0.15 if self.master_timer > 0 else 0.0

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
        self.ult_atk_timer = 0
    def hit_pre(self, t, arc):
        atk = min(self.yumina_stack * 0.04, 0.20)
        if self.ult_atk_timer > 0: atk += 0.30
        return 0.0, atk
    def on_hit(self, t, is_ult, cr_i):
        self.yumina_stack = min(self.yumina_stack + 1, 5)
    def post_action(self, t, is_ult, prob_none_crit, total_expected_crit_hits):
        if self.ult_atk_timer > 0: self.ult_atk_timer -= 1
        if is_ult: self.ult_atk_timer = 2
        gain = self.cdata.get("패시브", {}).get("치명타_행게_증가", 0.0)
        return (1.0 - prob_none_crit) * gain

class CharlesMechanic(Mechanic):
    def __init__(self, cname, cdata):
        super().__init__(cname, cdata)
        self.atk_timer = 0
    def hit_pre(self, t, arc):
        atk = 0.30 if self.atk_timer > 0 else 0.0
        di = 0.0
        if "럭키토큰" in t.get("note", ""): di += 0.05 # DEF piercing approximation (~5% dps increase)
        return di, atk
    def post_action(self, t, is_ult, prob_none_crit, total_expected_crit_hits):
        if self.atk_timer > 0: self.atk_timer -= 1
        if "추가턴" in t.get("note", "") and t.get("coeff", 1.0) == 0.0:
            self.atk_timer = 2
        return 0.0

def get_mechanic(cname, cdata):
    if cname.startswith("프레이"): return FreyMechanic(cname, cdata)
    if cname.startswith("로자리아"): return RosariaMechanic(cname, cdata)
    if cname == "리디아": return LydiaMechanic(cname, cdata)
    if cname.startswith("유미나"): return YuminaMechanic(cname, cdata)
    if cname.startswith("샤를"): return CharlesMechanic(cname, cdata)
    return Mechanic(cname, cdata)

def calculate_dps(cname, cdata, rdata, equip_name, arcana_name, journey_name):
    eq = EQUIPMENTS[equip_name]
    arc = ARCANAS[arcana_name]
    jr = JOURNEYS[journey_name]
    
    # Base Stats
    base_atk = cdata.get("기본_스탯", {}).get("공격력", 0)
    base_spd = cdata.get("기본_스탯", {}).get("속도", 100)
    base_cr = cdata.get("기본_스탯", {}).get("치명타_확률", 0.05)
    base_cd = cdata.get("기본_스탯", {}).get("치명타_피해", 0.50)
    
    res_pct = cdata.get("공명", {}).get("퍼센트", 0.0)
    if not res_pct: res_pct = cdata.get("공명", {}).get("공격력_퍼센트", 0.0)
    res_int = cdata.get("공명", {}).get("정수", 0.0)
    if not res_int: res_int = cdata.get("공명", {}).get("공격력_정수", 0.0)

    pool = (base_atk + 1250) * (1 + res_pct) + res_int
    
    # Passives & Statics
    passive_atk = cdata.get("패시브", {}).get("공격력_퍼센트", 0.0)
    passive_cr = cdata.get("패시브", {}).get("치확_퍼센트", 0.0)
    
    # Arcana Statics
    # Arcana Statics (Only those NOT handled dynamically in the loop)
    arc_spd_static = 8 if arc["type"] == "strikerB" else 0
    
    # Formula components
    # d_static includes everything that doesn't change turn-by-turn
    d_static = passive_atk + arc["atk"] + jr["atk_base"] + 0.01 + eq["atk"] + 0.1625
    final_spd = base_spd + 60 + arc_spd_static + eq.get("spd", 0)
    cr_base_total = base_cr + arc["cr"] + jr.get("cr", 0) + eq.get("cr", 0) + passive_cr
    cd_base_total = base_cd + arc["cd"] + jr.get("cd", 0) + eq.get("cd", 0)
    
    # Simulation Parameters
    MAX_ACTIONS = 20 # 2 cycles for steady state
    turns = rdata.get("turns", [])
    if not turns: return 0, 0, 0, 0
    
    cycle_time = 0.0
    total_dmg = 0.0
    max_hit = 0.0
    
    # Dynamic Tracking
    m = get_mechanic(cname, cdata)
    ax_stack = 0
    fx_carry = 0.0
    ga_reduction = 0.0
    ex_bonus_accum = 0.0
    
    # Arcana Stacks
    assassin_spd_stack = 0
    omega_dmg_stack = 0
    caster_cd_stack = 0
    
    # Ranger Stacks
    ra_cr_stack = 0
    ra_atk_stack = 0.0
    rc_spec_stack = 0
    rc_atk_stack = 0.0

    action_count = 0
    while action_count < MAX_ACTIONS:
        for t in turns:
            if action_count >= MAX_ACTIONS: break
            is_ult = t.get("is_ult", False)
            action_count += 1
            
            # 0. Arcana Stack Update (Turn Start)
            if arc["type"] == "assassin": assassin_spd_stack = min(assassin_spd_stack + 1, 3)
            if arc["type"] in ["strikerA", "strikerC", "strikerD", "casterB", "casterC", "rangerB"]:
                omega_dmg_stack = min(omega_dmg_stack + 1, 5)
            if arc["type"] in ["casterA", "casterB", "casterC"]:
                caster_cd_stack = min(caster_cd_stack + 1, 3)

            # 1. Gauge & Time
            spd_i = (final_spd + assassin_spd_stack * 10) * (t.get("spd_mult", 1.0) + m.get_spd_mult())
            if spd_i > 0:
                cycle_time += (1000.0 / spd_i) * (1.0 - ga_reduction)
            ga_reduction = 0.0
            
            # 2. AX Stack Update
            if jr["type"] == "AX": ax_stack = min(ax_stack + 1, 5)

            # 3. Hit List
            base_hits = t.get("hits", 4 if is_ult else 1)
            hit_list = []
            if t.get("coeff", 0.0) > 0:
                hit_list.extend([t["coeff"] / base_hits] * base_hits)
            if t.get("extra_coeff", 0.0) > 0:
                hit_list.append(t["extra_coeff"])
            
            # Rosaria Auto-Bonus
            if cname.startswith("로자리아") and (not is_ult) and t.get("is_basic", False):
                 if getattr(m, 'stacks', {}).get("upwa", 0) >= 3.0:
                      if t.get("extra_coeff", 0.0) == 0: hit_list.append(1.50)

            turn_dmg = 0.0
            prob_none_crit = 1.0
            expected_crits = 0.0
            
            # 4. Turn Buffs
            t_atk_buf = t.get("atk_buf", 0.0)
            t_di = t.get("di", 0.0)
            t_cr = t.get("cr_buf", 0.0)
            t_cd = t.get("cd_buf", 0.0)
            
            # 5. Hit Loop
            for hit in hit_list:
                m_di, m_atk = m.hit_pre(t, arc)
                
                # Ranger CR Stack (5% each)
                ra_cr_bonus = (ra_cr_stack * 0.05) if "레인저" in arc["class"] else 0.0
                cr_i = min(cr_base_total + t_cr + ra_cr_bonus, 1.0)
                cd_i = cd_base_total + t_cd + (caster_cd_stack * 0.10)
                
                crit_contrib = cr_i * cd_i
                prob_none_crit *= (1.0 - cr_i)
                expected_crits += cr_i
                
                # Dynamic Atk Buffs [SUM then MULTIPLY]
                ra_atk_bonus = (ra_atk_stack * 0.03) if arc["type"] == "rangerA" else 0.0
                rc_atk_bonus = (rc_atk_stack * 0.03) if arc["type"] in ["rangerC", "rangerD"] else 0.0
                ax_val = (ax_stack * 0.08) if jr["type"] == "AX" else 0.0
                
                total_dyn_atk = t_atk_buf + ra_atk_bonus + rc_atk_bonus + m_atk + ax_val
                
                eff_base = pool * (1 + d_static) + 1000
                eff_atk = eff_base * (1 + total_dyn_atk)
                
                # DI Sum
                omega_di = (omega_dmg_stack * 0.05) if t.get("omega_elig", False) else 0.0
                rc_spec_di = (rc_spec_stack * 0.05) if arc["type"] in ["rangerC", "rangerD"] else 0.0
                total_di = t_di + omega_di + fx_carry + rc_spec_di + m_di
                
                dmg = (eff_atk * hit) * (1 + total_di + crit_contrib)
                turn_dmg += dmg
                
                # On-Hit Logic
                if "레인저" in arc["class"] and t.get("is_basic", False):
                    ra_cr_stack = min(ra_cr_stack + 1, 5)
                if is_ult:
                    if arc["type"] == "rangerA": ra_atk_stack = min(ra_atk_stack + cr_i, 5.0)
                    if arc["type"] in ["rangerC", "rangerD"]: rc_atk_stack = min(rc_atk_stack + cr_i, 5.0)
                
                m.on_hit(t, is_ult, cr_i)

            # 6. Post-Action Logic
            ga_reduction = m.post_action(t, is_ult, prob_none_crit, expected_crits)
            
            if jr["type"] == "FX" and hit_list:
                fx_carry = (1.0 - prob_none_crit) * 0.25
            if jr["type"] == "EX" and t.get("is_basic", False):
                ex_bonus_accum += (1.0 - prob_none_crit) * 0.25 * 16215
            
            is_spec = (not t.get("is_basic", False)) and (not is_ult) and t.get("coeff", 0) > 0
            if is_spec and arc["type"] in ["rangerB", "rangerC", "rangerD"]:
                rc_spec_stack = min(rc_spec_stack + 1, 5)
                
            if is_ult and jr["type"] == "AX":
                ax_stack = 0
            
            total_dmg += turn_dmg
            max_hit = max(max_hit, turn_dmg)

    total_dmg += ex_bonus_accum
    if cycle_time <= 0: return 0,0,0,0
    
    return total_dmg / cycle_time, total_dmg, cycle_time, max_hit

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
