
import json
import re
import math
import csv
import pandas as pd

# --- Configuration & Data Loading ---

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
    "레인저B":     {"class": ["레인저"], "atk": 0.06, "cr": 0.24, "cd": 0.00, "type": "rangerB"},
    "레인저C":     {"class": ["레인저"], "atk": 0.00, "cr": 0.18, "cd": 0.12, "type": "rangerC"},
    "레인저D":     {"class": ["레인저"], "atk": 0.06, "cr": 0.24, "cd": 0.12, "type": "rangerD"},
    "레인저(유미나 전용)": {"class": ["레인저"], "atk": 0.06, "cr": 0.24, "cd": 0.12, "type": "yumina_exclusive"}
}

EQUIPMENTS = {
    "공격4세트": {"atk": 0.20, "cr": 0.0, "cd": 0.0, "spd": 0, "hp": 0.0},
    "파괴4세트": {"atk": 0.00, "cr": 0.0, "cd": 0.40, "spd": 0, "hp": 0.0},
    "통찰4세트": {"atk": 0.00, "cr": 0.30, "cd": 0.0, "spd": 0, "hp": 0.0},
    "속도4세트": {"atk": 0.00, "cr": 0.0, "cd": 0.0, "spd": 15, "hp": 0.0},
}

def extract_json_from_md(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    blocks = re.findall(r"```json\n(.*?)\n```", content, re.DOTALL)
    data = {}
    for b in blocks:
        try:
            j = json.loads(b)
            if "이름" in j:
                data[j["이름"]] = j
            else:
                data.update(j)
        except Exception as e:
            pass
    return data

SPECS = extract_json_from_md("Data/캐릭터_스펙_마스터.md")
ROTATIONS = extract_json_from_md("Data/사이클_로테이션_마스터.md")

# --- Simulation Logic ---

class CharacterState:
    def __init__(self, name_query, arc_name, eq_name, jr_type):
        self.name = None
        for k in SPECS.keys():
            if name_query in k:
                self.name = k
                break
        
        if not self.name or self.name not in ROTATIONS:
             raise ValueError(f"Character query '{name_query}' not found.")
             
        self.cdata = SPECS[self.name]
        self.rdata = ROTATIONS[self.name]
        self.arc = ARCANAS[arc_name]
        self.eq = EQUIPMENTS[eq_name]
        self.jr_type = jr_type
        
        # Base Stats
        self.base_atk = self.cdata["기본_스탯"]["공격력"]
        self.base_spd = self.cdata["기본_스탯"]["속도"]
        self.cr_base = self.cdata["기본_스탯"]["치명타_확률"]
        self.cd_base = self.cdata["기본_스탯"]["치명타_피해"]
        
        # Passives & Resonance
        self.pass_atk_p = self.cdata.get("패시브", {}).get("공격력_퍼센트", 0.0)
        self.pass_cr_p = self.cdata.get("패시브", {}).get("치확_퍼센트", 0.0)
        self.res_cr_p = self.cdata.get("공명", {}).get("치확_퍼센트", 0.0)
        
        # Gauge & Stacks
        self.gauge = 0.0
        self.turn_count = 0
        self.ax_stack = 0
        self.assassin_spd_stack = 0
        self.omega_dmg_stack = 0
        self.caster_cd_stack = 0
        self.ra_cr_stack = 0
        self.rc_spec_stack = 0
        self.total_damage = 0.0
        
    def get_current_spd(self):
        # Base + Equipment stats + Standard Substats (+60)
        extra_spd = 0
        if self.arc["type"] == "스트라이커B": extra_spd = 8
        final_base_spd = self.base_spd + self.eq.get("spd", 0) + extra_spd + 60
        
        # Stacks (Assassin speed stack)
        current_spd = final_base_spd + (self.assassin_spd_stack * 10)
        
        # Rotation Modifier (spd_mult from JSON)
        loop = self.rdata["turns"]
        t = loop[self.turn_count % len(loop)]
        spd_mult = t.get("spd_mult", 1.0)
        
        return current_spd * spd_mult

    def take_turn(self):
        loop = self.rdata["turns"]
        t = loop[self.turn_count % len(loop)]
        is_ult = t.get("is_ult", False)
        is_basic = t.get("is_basic", False)
        self.turn_count += 1
        
        # Turn Start Updates
        if self.arc["type"] == "assassin": self.assassin_spd_stack = min(self.assassin_spd_stack + 1, 3)
        if self.jr_type == "AX": self.ax_stack = min(self.ax_stack + 1, 5)
        if self.arc["type"] in ["casterA", "casterB", "casterC"]:
            self.caster_cd_stack = min(self.caster_cd_stack + 1, 3)

        # Damage Calculation
        total_atk_p = self.pass_atk_p + self.eq["atk"] + self.arc["atk"] + t.get("atk_buf", 0.0)
        eff_base = (self.base_atk + 1250) * (1.0 + total_atk_p + self.cdata.get("공명", {}).get("퍼센트", 0)) + self.cdata.get("공명", {}).get("정수", 0)
        if self.jr_type == "AX" and is_ult:
            eff_base *= (1.0 + self.ax_stack * 0.08)
        
        total_di = t.get("di", 0.0)
        if self.arc["type"] in ["strikerA", "strikerC", "strikerD", "casterB", "casterC"]:
             if (not is_basic) and (not is_ult) and t.get("coeff", 0) > 0:
                 self.omega_dmg_stack = min(self.omega_dmg_stack + 1, 5)
             total_di += self.omega_dmg_stack * 0.05
        
        if self.arc["type"] in ["rangerB", "rangerC", "rangerD", "yumina_exclusive"]:
             if (not is_basic) and (not is_ult) and t.get("coeff", 0) > 0:
                 self.rc_spec_stack = min(self.rc_spec_stack + 1, 5)
             total_di += self.rc_spec_stack * 0.05

        ra_cr_bonus = 0.0
        if self.arc["class"] == ["레인저"]:
             if is_basic or t.get("extra_coeff", 0) > 0:
                 self.ra_cr_stack = min(self.ra_cr_stack + 1, 5)
             ra_cr_bonus = self.ra_cr_stack * 0.05
        
        cr_i = min(self.cr_base + self.pass_cr_p + self.res_cr_p + self.eq["cr"] + self.arc["cr"] + t.get("cr_buf", 0.0) + ra_cr_bonus, 1.0)
        cd_i = self.cd_base + self.eq["cd"] + self.arc["cd"] + self.caster_cd_stack * 0.10 + t.get("cd_buf", 0.0)
        
        coeff = t.get("coeff", 0.0) + t.get("extra_coeff", 0)
        # Additive Damage Formula (as per V7 Official Guide)
        # Total_DI = Skill_DI + Omega_DI + CD_Bonus (Expected)
        total_di_all = total_di + (cr_i * cd_i)
        
        turn_dmg = eff_base * coeff * (1.0 + total_di_all)
        self.total_damage += turn_dmg
        
        # Reset Gauge
        self.gauge = 0.0
        
        if "유미나" in self.name:
             # Hypothesis: Per Hit gain instead of Per Action.
             # gain = 0.15 * Expected_Hits_that_Crit
             hits = t.get("hits", 4 if is_ult else 1)
             expected_crits = hits * cr_i
             self.gauge += 0.15 * expected_crits
             
        if t.get("note") and "행게+30%" in t["note"]:
             self.gauge += 0.30
             
        if is_ult and self.jr_type == "AX": self.ax_stack = 0
        
        return turn_dmg

def run_party_simulation(member_configs, target_turns=50):
    states = [CharacterState(**cfg) for cfg in member_configs]
    total_actions = 0
    while total_actions < target_turns:
        times = []
        for s in states:
            spd = s.get_current_spd()
            if spd <= 0: spd = 1
            times.append((1.0 - s.gauge) * (1000.0 / spd))
        min_time = min(times)
        for s in states:
            spd = s.get_current_spd()
            s.gauge = min(1.0, s.gauge + (spd * min_time) / 1000.0)
        ready_chars = [s for s in states if s.gauge >= 0.9999]
        if ready_chars:
            ready_chars[0].take_turn()
            total_actions += 1
    
    results = []
    total_party_dmg = sum(s.total_damage for s in states)
    for s in states:
        results.append({
            "Character": s.name,
            "Turns": s.turn_count,
            "Total Damage": round(s.total_damage, 2),
            "Share": round((s.total_damage / total_party_dmg) * 100, 2)
        })
    return results, total_party_dmg

if __name__ == "__main__":
    TURNS = 200
    party_atk = [
        {"name_query": "로자리아", "arc_name": "레인저D", "eq_name": "공격4세트", "jr_type": "AX"},
        {"name_query": "유미나", "arc_name": "레인저(유미나 전용)", "eq_name": "공격4세트", "jr_type": "AX"},
        {"name_query": "리디아", "arc_name": "레인저D", "eq_name": "파괴4세트", "jr_type": "AX"},
        {"name_query": "레이시", "arc_name": "레인저D", "eq_name": "공격4세트", "jr_type": "AX"}
    ]
    party_ins = [
        {"name_query": "로자리아", "arc_name": "레인저D", "eq_name": "공격4세트", "jr_type": "AX"},
        {"name_query": "유미나", "arc_name": "레인저(유미나 전용)", "eq_name": "통찰4세트", "jr_type": "AX"},
        {"name_query": "리디아", "arc_name": "레인저D", "eq_name": "파괴4세트", "jr_type": "AX"},
        {"name_query": "레이시", "arc_name": "레인저D", "eq_name": "공격4세트", "jr_type": "AX"}
    ]
    
    print(f"Running Long-term Simulation ({TURNS} total turns)...\n")
    res_atk, _ = run_party_simulation(party_atk, TURNS)
    res_ins, _ = run_party_simulation(party_ins, TURNS)
    
    df_atk = pd.DataFrame(res_atk)
    df_ins = pd.DataFrame(res_ins)
    
    print("### RESULTS: YUMINA (ATTACK SET) ###")
    print(df_atk[df_atk['Character'].str.contains('유미나')].to_string(index=False))
    print("\n### RESULTS: YUMINA (INSIGHT SET) ###")
    print(df_ins[df_ins['Character'].str.contains('유미나')].to_string(index=False))
