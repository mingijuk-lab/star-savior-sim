import json
import re
import csv
import itertools

def extract_json_from_md(filepath):
    """Extracts all JSON blocks from a markdown file and merges them."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    json_blocks = re.findall(r'```json\s+(.*?)\s+```', content, re.DOTALL)
    parsed_data = {}
    for block in json_blocks:
        try:
            block = re.sub(r'([0-9.]+)\+([0-9.]+)', lambda m: str(float(m.group(1)) + float(m.group(2))), block)
            if block.strip().startswith('"'):
                data = json.loads("{" + block + "}")
                parsed_data.update(data)
            else:
                data = json.loads(block)
                if "이름" in data: parsed_data[data["이름"]] = data
                else: parsed_data.update(data)
        except: continue
    return parsed_data

EQUIPMENTS = {
    "공격4세트": {"atk": 0.20, "cr": 0.0, "cd": 0.0, "spd": 0},
    "통찰4세트": {"atk": 0.00, "cr": 0.30, "cd": 0.0, "spd": 0},
    "파괴4세트": {"atk": 0.00, "cr": 0.0, "cd": 0.40, "spd": 0, "hp": 0.00},
    "속도4세트": {"atk": 0.00, "cr": 0.0, "cd": 0.0, "spd": 15, "hp": 0.00},
    "체력4세트": {"atk": 0.00, "cr": 0.0, "cd": 0.0, "spd": 0, "hp": 0.30},
}

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

JOURNEYS = {
    "AX": {"atk_base": 0.08, "cr": 0.0, "cd": 0.0, "type": "AX"},
    "FX": {"atk_base": 0.00, "cr": 0.0, "cd": 0.10, "type": "FX"},
    "EX": {"atk_base": 0.00, "cr": 0.10, "cd": 0.00, "type": "EX"},
    "GX": {"atk_base": 0.00, "cr": 0.00, "cd": 0.00, "type": "GX"}
}

def calculate_dps(cname, cdata, rdata, eq_name, arc_name, jr_name, max_actions=10):
    eq, arc, jr = EQUIPMENTS[eq_name], ARCANAS[arc_name], JOURNEYS[jr_name]
    res = cdata.get("공명", {})
    ax_fixed = 0.08 if jr["type"] == "AX" else 0.0
    pool = (cdata["기본_스탯"]["공격력"] + 1250) * (1.0 + res.get("퍼센트", 0) + ax_fixed) + res.get("정수", 0)
    final_spd = cdata["기본_스탯"]["속도"] + 60 + (8 if arc["type"] == "strikerB" else 0) + eq.get("spd", 0)
    total_dmg, cycle_time, ga_red_carry, omega_dmg_stack, assassin_spd_stack, caster_cd_stack, ra_cr_stack, ax_stack = 0.0, 0.0, 0.0, 0, 0, 0, 0, 1
    bleeding_dots = []

    for action_idx in range(max_actions):
        t = rdata["turns"][action_idx % len(rdata["turns"])]
        is_ult, is_basic = t.get("is_ult", False), t.get("is_basic", False)
        is_spec = (not is_basic) and (not is_ult) and t.get("coeff", 0) > 0
        
        if arc["type"] == "assassin": assassin_spd_stack = min(assassin_spd_stack + 1, 3)
        if arc["type"].startswith("caster"): caster_cd_stack = min(caster_cd_stack + 1, 3)
        if arc["class"] == ["레인저"] and (is_basic or t.get("extra_coeff", 0) > 0): ra_cr_stack = min(ra_cr_stack + 1, 5)

        spd_i = (final_spd + assassin_spd_stack * 10) * t.get("spd_mult", 1.0)
        cycle_time += (1000.0 / spd_i) * (1.0 - ga_red_carry)
        
        # 0. Omega Stacking (Corrected Inclusion)
        if arc["type"] in ["strikerA", "strikerC", "strikerD", "casterB", "casterC", "rangerB", "rangerC", "rangerD"]:
            if is_spec: omega_dmg_stack = min(omega_dmg_stack + 1, 5)

        m_di, m_atk_mult, coeff = 0.0, 1.0, t.get("coeff", 0) + t.get("extra_coeff", 0)
        for k, v in t.items():
            if k.endswith("_di"): m_di += v
            if k.endswith("_atk_p"): m_atk_mult *= (1.0 + v)
            if k.startswith("yumina_stack"): m_atk_mult *= (1.0 + v * 0.04)
            if k.startswith("lydia_stack"): m_atk_mult *= (1.0 + v * 0.06)
            if k.startswith("doyak"): m_di += (0.30 if v >= 5 else 0)
        
        ax_dyn = (ax_stack * 0.08) if jr["type"] == "AX" else 0.0
        base_atk_p = cdata.get("패시브", {}).get("공격력_퍼센트", 0) + eq["atk"] + arc["atk"] + 0.1625 + 0.01
        # V6: eff_atk = eff_base * (1 + AX_dyn + Skill_Buff)
        eff_base = pool * (1.0 + base_atk_p) + 1000
        eff_atk = eff_base * (1.0 + ax_dyn + t.get("atk_buf", 0)) * m_atk_mult
        
        cr_i = min(cdata["기본_스탯"]["치명타_확률"] + eq["cr"] + arc["cr"] + t.get("cr_buf", 0) + ra_cr_stack * 0.05 + res.get("치확_퍼센트", 0) + jr.get("cr", 0), 1.0)
        cd_i = cdata["기본_스탯"]["치명타_피해"] + eq["cd"] + arc["cd"] + caster_cd_stack * 0.10 + t.get("cd_buf", 0) + jr.get("cd", 0)
        
        # 1. Omega Boost Application (Corrected Application Turn)
        omega_boost = (omega_dmg_stack * 0.05) if (is_spec or t.get("omega_elig", False)) else 0.0
        total_di = t.get("di", 0) + m_di + omega_boost

        turn_dmg = eff_atk * coeff * (1.0 + total_di + cr_i * cd_i)
        
        # DOT
        bleed_count = 2 if is_ult else (2 if ("yumina_stack" in t and t["yumina_stack"] >= 5) else (1 if ("유미나" in cname and (not is_basic)) else 0))
        if bleed_count > 0: bleeding_dots.append({"turns": 2, "atk": eff_atk * bleed_count, "di": total_di})
        if jr["type"] == "GX" and is_basic: bleeding_dots.append({"turns": 2, "atk": eff_atk * 0.5, "di": total_di})
        
        tick_dmg = 0
        for dot in bleeding_dots:
            tick_dmg += dot["atk"] * 0.25 * (1 + dot["di"])
            dot["turns"] -= 1
        bleeding_dots = [d for d in bleeding_dots if d["turns"] > 0]
        
        total_dmg += turn_dmg + tick_dmg
        
        hits = t.get("hits", 4 if is_ult else 1)
        prob_crit_any = (1.0 - (1.0 - cr_i) ** hits)
        ga_red_carry = 0.0
        if is_basic and "유미나" in cname: ga_red_carry += prob_crit_any * 0.15
        if is_ult and "리디아" in cname: ga_red_carry += 0.30
        if t.get("note") and "행게+30%" in t["note"]: ga_red_carry += 0.30
        if t.get("note") and "행게+50%" in t["note"]: ga_red_carry += 0.50
        
        if jr["type"] == "AX":
            if is_ult: ax_stack = 1
            else: ax_stack = min(ax_stack + 1, 5)

    return (total_dmg / cycle_time) if cycle_time > 0 else 0, total_dmg, cycle_time, total_dmg

def main():
    specs, rotations = extract_json_from_md("Data/캐릭터_스펙_마스터.md"), extract_json_from_md("Data/사이클_로테이션_마스터.md")
    results = []
    for cname, cdata in specs.items():
        if cname not in rotations or cdata.get("분류") == "디펜더": continue
        for eq_n in EQUIPMENTS.keys():
            for arc_n, arc_d in ARCANAS.items():
                if cdata.get("분류") not in arc_d["class"]: continue
                if "전용" in arc_n and ("유미나" not in cname and "레이시" not in arc_n): continue
                for jr_n in JOURNEYS.keys():
                    for t_limit in [5, 10, 15]:
                        dps, total, time, _ = calculate_dps(cname, cdata, rotations[cname], eq_n, arc_n, jr_n, t_limit)
                        results.append({"Character": cname, "Class": cdata["분류"], "Equip": eq_n, "Arcana": arc_n, "Journey": jr_n, "Turns": t_limit, "DPS": round(dps, 2)})
    
    results.sort(key=lambda x: (x["Character"], x["Turns"], -x["DPS"]))
    
    # Generate Growth Logic
    growth_data = []
    for cname, cdata in specs.items():
        if cname not in rotations or cdata.get("분류") == "디펜더": continue
        rdata = rotations[cname]
        
        # Threshold Solver Logic (Integrated)
        res = cdata.get("공명", {})
        pool = (cdata["기본_스탯"]["공격력"] + 1250) * (1.14) + res.get("정수", 0) # Base + AX8% + Resonance
        arc_atk = (0.14 if cdata["분류"] in ["스트라이커", "어쌔신", "캐스터"] else 0.06)
        sa = cdata.get("패시브", {}).get("공격력_퍼센트", 0) + arc_atk + 0.1625 + 0.01
        cr = cdata["기본_스탯"]["치명타_확률"] + 0.30 + (0.30 if "클레어" in cname else 0)
        di = 0.55 # Average DI including Omega
        
        atk_mult = (pool * (1.0 + sa + 0.20) + 1000) / (pool * (1.0 + sa) + 1000)
        num = (atk_mult - 1) * (1 + di)
        den = (0.3 + cr - atk_mult * cr)
        cd_threshold = (num / den) if den != 0 else 9.99
        
        # Smart Recommendation
        rec = "Attack (초기)"
        if cr > 0.75: rec = "파괴 (만치확)"
        elif cd_threshold < 0.85: rec = "통찰/파괴 (고치피)"
        
        growth_data.append(f"| {cname:15} | {cr:7.1%} | {cd_threshold:10.1%} | {rec:15} |")

    # Write Output Files
    with open("Results/dps_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["Character", "Class", "Equip", "Arcana", "Journey", "Turns", "DPS"])
        writer.writeheader(); writer.writerows(results)
    
    with open("Results/optimization_guide.md", "w", encoding="utf-8") as f:
        f.write("# 📊 장비 최적화 가이드 (자동 생성)\n\n")
        f.write("| 캐릭터 | 실전 기본치확 | 치피 임계점 | 추천 세트 | \n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        f.write("\n".join(growth_data))
        f.write("\n\n* 임계점: 해당 치피를 넘기면 통찰/파괴 세트가 공격 세트보다 강력해집니다.\n")

if __name__ == "__main__": main()
