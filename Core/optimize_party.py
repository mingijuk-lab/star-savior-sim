
import json
import re
import math
import csv
import pandas as pd
import itertools
from multiprocessing import Pool, cpu_count

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
    "공격4세트": {"atk": 0.20, "cr": 0.0, "cd": 0.0, "spd": 0},
    "파괴4세트": {"atk": 0.00, "cr": 0.0, "cd": 0.40, "spd": 0},
    "통찰4세트": {"atk": 0.00, "cr": 0.30, "cd": 0.0, "spd": 0},
}

def extract_json_from_md(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    blocks = re.findall(r"```json\n(.*?)\n```", content, re.DOTALL)
    data = {}
    for b in blocks:
        try:
            j = json.loads(b)
            if "이름" in j: data[j["이름"]] = j
            else: data.update(j)
        except: pass
    return data

SPECS = extract_json_from_md("Data/캐릭터_스펙_마스터.md")
ROTATIONS = extract_json_from_md("Data/사이클_로테이션_마스터.md")

class CharacterState:
    def __init__(self, name_query, arc_name, eq_name, jr_type):
        self.name = next((k for k in SPECS.keys() if name_query in k), None)
        if not self.name: raise ValueError(f"{name_query} not found.")
        self.cdata, self.rdata = SPECS[self.name], ROTATIONS[self.name]
        self.arc, self.eq, self.jr_type = ARCANAS[arc_name], EQUIPMENTS[eq_name], jr_type
        self.base_atk = self.cdata["기본_스탯"]["공격력"]
        self.base_spd = self.cdata["기본_스탯"]["속도"]
        res = self.cdata.get("공명", {})
        ax_fixed = 0.08 if self.jr_type == "AX" else 0.0
        self.pool = (self.base_atk + 1250) * (1.0 + res.get("퍼센트", 0) + ax_fixed) + res.get("정수", 0)
        self.gauge, self.turn_count, self.total_damage, self.ax_stack = 0.0, 0, 0.0, 1
        self.assassin_spd_stack, self.omega_dmg_stack, self.caster_cd_stack, self.ra_cr_stack = 0, 0, 0, 0

    def take_turn(self):
        loop = self.rdata["turns"]
        t = loop[self.turn_count % len(loop)]
        is_ult, is_basic = t.get("is_ult", False), t.get("is_basic", False)
        is_spec = (not is_basic) and (not is_ult) and t.get("coeff", 0) > 0
        self.turn_count += 1
        
        if self.arc["type"] == "assassin": self.assassin_spd_stack = min(self.assassin_spd_stack + 1, 3)
        if self.arc["type"].startswith("caster"): self.caster_cd_stack = min(self.caster_cd_stack + 1, 3)
        if self.arc["class"] == ["레인저"] and (is_basic or t.get("extra_coeff", 0) > 0): self.ra_cr_stack = min(self.ra_cr_stack + 1, 5)
        
        # Fixed Omega Stacking
        if self.arc["type"] in ["strikerA", "strikerC", "strikerD", "casterB", "casterC", "rangerB", "rangerC", "rangerD"]:
            if is_spec: self.omega_dmg_stack = min(self.omega_dmg_stack + 1, 5)

        m_di, m_atk_mult, coeff = 0.0, 1.0, t.get("coeff", 0) + t.get("extra_coeff", 0)
        for k, v in t.items():
            if k.endswith("_di"): m_di += v
            if k.endswith("_atk_p"): m_atk_mult *= (1.0 + v)
            if k.startswith("yumina_stack"): m_atk_mult *= (1.0 + v * 0.04)
            if k.startswith("lydia_stack"): m_atk_mult *= (1.0 + v * 0.06)
            if k.startswith("doyak"): m_di += (0.30 if v >= 5 else 0)

        ax_dyn = (self.ax_stack * 0.08) if self.jr_type == "AX" else 0.0
        base_atk_p = self.cdata.get("패시브", {}).get("공격력_퍼센트", 0) + self.eq["atk"] + self.arc["atk"] + t.get("atk_buf", 0) + 0.1625 + 0.01
        eff_atk = self.pool * (1.0 + base_atk_p + ax_dyn) * m_atk_mult + 1000
        if self.jr_type == "AX" and is_ult: eff_atk *= 1.40 
        
        cr_i = min(self.cdata["기본_스탯"]["치명타_확률"] + self.eq["cr"] + self.arc["cr"] + t.get("cr_buf", 0) + self.ra_cr_stack * 0.05 + self.cdata.get("공명", {}).get("치확_퍼센트", 0), 1.0)
        cd_i = self.cdata["기본_스탯"]["치명타_피해"] + self.eq["cd"] + self.arc["cd"] + self.caster_cd_stack * 0.10 + t.get("cd_buf", 0)
        
        # Fixed Omega Application
        omega_boost = (self.omega_dmg_stack * 0.05) if (is_spec or t.get("omega_elig", False)) else 0.0
        total_di = t.get("di", 0) + m_di + omega_boost
        
        dmg = eff_atk * coeff * (1.0 + total_di + cr_i * cd_i)
        self.total_damage += dmg
        
        hits = t.get("hits", 4 if is_ult else 1)
        p_crit = (1.0 - (1.0 - cr_i) ** hits)
        self.gauge = 0.0
        if is_basic and "유미나" in self.name: self.gauge += p_crit * 0.15
        if is_ult and "리디아" in self.name: self.gauge += 0.30
        if t.get("note") and "행게+30%" in t["note"]: self.gauge += 0.30
        if t.get("note") and "행게+50%" in t["note"]: self.gauge += 0.50
        if self.jr_type == "AX":
            if is_ult: self.ax_stack = 1
            else: self.ax_stack = min(self.ax_stack + 1, 5)
        return dmg

def run_sim_unpacker(args):
    config, turns = args
    states = [CharacterState(**c) for c in config]
    total_actions = 0
    while total_actions < turns:
        times = [((1.0 - s.gauge) * 1000.0 / (cur := (s.base_spd + s.eq.get("spd", 0) + 60 + (8 if s.arc["type"] == "strikerB" else 0) + s.assassin_spd_stack * 10) * s.rdata["turns"][s.turn_count % len(s.rdata["turns"])].get("spd_mult", 1.0))) for s in states]
        min_t = min(times); min_t = max(min_t, 0.001)
        for s in states:
            cur_spd = (s.base_spd + s.eq.get("spd", 0) + 60 + (8 if s.arc["type"] == "strikerB" else 0) + s.assassin_spd_stack * 10) * s.rdata["turns"][s.turn_count % len(s.rdata["turns"])].get("spd_mult", 1.0)
            s.gauge = min(1.0, s.gauge + cur_spd * min_t / 1000.0)
        ready = [s for s in states if s.gauge >= 0.9999]; ready[0].take_turn(); total_actions += 1
    total_dmg = sum(s.total_damage for s in states)
    return config, total_dmg

def optimize_party_grid(char_names, jr_type="AX", turns=50):
    member_search_space = []
    for name in char_names:
        full_name = next((k for k in SPECS.keys() if name in k), None)
        cclass = SPECS[full_name]["분류"]
        valid_arcs = [a_n for a_n, a_d in ARCANAS.items() if (cclass in a_d["class"])]
        valid_arcs = [a for a in valid_arcs if ("전용" not in a) or (name in a)]
        options = [{"name_query": name, "arc_name": a, "eq_name": e, "jr_type": jr_type} for e in EQUIPMENTS.keys() for a in valid_arcs]
        member_search_space.append(options)
    combinations = list(itertools.product(*member_search_space))
    tasks = [(list(combo), turns) for combo in combinations]
    with Pool(cpu_count()) as p: results = p.map(run_sim_unpacker, tasks)
    results.sort(key=lambda x: x[1], reverse=True)
    return results

if __name__ == "__main__":
    PARTY_NAMES = ["로자리아", "유미나", "리디아", "레이시"]
    top_results = optimize_party_grid(PARTY_NAMES)
    report_file = "Results/party_optimization_raw.csv"
    with open(report_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Rank", "Total Damage", "Member 1 EQ", "Member 1 Arc", "Member 2 EQ", "Member 2 Arc", "Member 3 EQ", "Member 3 Arc", "Member 4 EQ", "Member 4 Arc"])
        for i, (config, dmg) in enumerate(top_results[:100]):
            row = [i+1, round(dmg, 0)]
            for c in config: row.extend([c["eq_name"], c["arc_name"]])
            writer.writerow(row)
    print(f"\nOptimization Finished. Top 1: {top_results[0][1]:,.0f} Damage\n")
