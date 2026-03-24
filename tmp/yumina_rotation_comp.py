import json
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extract_json_from_md(filepath):
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

def run_sim_rotation(rotation_pattern, journey_type="AX"):
    specs = extract_json_from_md("d:/Star/Data/캐릭터_스펙_마스터.md")
    cname = "유미나"
    cdata = specs[cname]
    
    # Base Stats (Standard Destruction + Exclusive Arcana)
    pool = 5606
    d_static = 0.15 + 0.1625 + 0.01 + 0.06 + 0.08
    if journey_type == "GX": d_static -= 0.08
    
    base_spd = 100
    base_cr = 0.11 + 0.24 # Base + Arcana
    base_cd = 0.50 + 0.12 + 0.40 # Base + Arcana + Destruction
    
    final_spd = base_spd + 60
    
    yumina_stack = 0
    ax_stack = 0
    bleeding_dots = []
    
    total_dmg = 0
    cycle_time = 0
    MAX_ACTIONS = 15
    
    for i in range(MAX_ACTIONS):
        # Determine current action based on pattern
        act_idx = i % 5
        is_ult = False
        is_spec = False
        is_basic = False
        
        t_atk_buf = 0
        t_cr_buf = 0
        coeff = 0
        di = 0.15
        
        # Buff timers (simplified logic based on typical 2nd sequence)
        # Ult-First: U, S, B, B, B
        # Spec-First: S, U, B, B, B
        
        # Check buffs from previous actions
        if rotation_pattern == "Ult-First":
            # Ult at 0, 5, 10
            # Spec at 1, 6, 11
            # Ult Atk Buff (2 turns): At 0, 1 (T1, T2)
            # Spec CR Buff (2 turns): At 1, 2 (T2, T3)
            if act_idx in [0, 1]: t_atk_buf = 0.30
            if act_idx in [1, 2]: t_cr_buf = 0.30
            
            if act_idx == 0: is_ult, coeff = True, 1.525
            elif act_idx == 1: is_spec, coeff = True, 1.90
            else: is_basic, coeff = True, 1.50
            
        else: # Spec-First
            # Spec at 0, 5, 10
            # Ult at 1, 6, 11
            # Spec CR Buff (2 turns): At 0, 1 (T1, T2)
            # Ult Atk Buff (2 turns): At 1, 2 (T2, T3)
            if act_idx in [0, 1]: t_cr_buf = 0.30
            if act_idx in [1, 2]: t_atk_buf = 0.30
            
            if act_idx == 0: is_spec, coeff = True, 1.90
            elif act_idx == 1: is_ult, coeff = True, 1.525
            else: is_basic, coeff = True, 1.50

        # Simulation Logic
        spd_i = final_spd
        cycle_time += 1000.0 / spd_i
        
        if journey_type == "AX": ax_stack = min(ax_stack + 1, 5)
        
        m_atk = min(yumina_stack * 0.04, 0.20)
        ax_val = (ax_stack * 0.08) if journey_type == "AX" else 0.0
        total_dyn_atk = t_atk_buf + m_atk + ax_val
        
        eff_base = pool * (1 + d_static) + 1000
        eff_atk = eff_base * (1 + total_dyn_atk)
        
        cr_i = min(base_cr + t_cr_buf, 1.0)
        crit_contrib = cr_i * (base_cd)
        
        total_dmg += (eff_atk * coeff) * (1 + di + crit_contrib)
        
        # Bleed (Simplifying based on 1.6 avg stack AX or 2.2 GX logic from previous analysis)
        # Bleed for Ult(2), Spec(2 if stack>=5 else 1)
        m_bleed_count = 0
        if is_ult: m_bleed_count = 2
        elif is_spec: m_bleed_count = 2 if yumina_stack >= 5 else 1
        
        if m_bleed_count > 0:
            bleeding_dots.append({"turns": 2, "atk": eff_atk * m_bleed_count})
        if journey_type == "GX" and is_basic:
            bleeding_dots.append({"turns": 2, "atk": eff_atk * 0.5})
            
        for dot in bleeding_dots:
            total_dmg += dot["atk"] * 0.25 * (1 + di)
            dot["turns"] -= 1
        bleeding_dots = [d for d in bleeding_dots if d["turns"] > 0]
        
        yumina_stack = min(yumina_stack + 1, 5)
        if is_ult and journey_type == "AX": ax_stack = 0
        
    return total_dmg / cycle_time

print("### 유미나 사이클 우선순위 비교 (AX 여정 기준) ###\n")
uf_dps = run_sim_rotation("Ult-First")
sf_dps = run_sim_rotation("Spec-First")
diff = (uf_dps / sf_dps - 1) * 100

print(f"| 사이클 유형 | 설명 | DPS |")
print(f"| :--- | :--- | :---: |")
print(f"| **궁극기 우선 (Ult-First)** | Ult(공버프) -> Spec(치확/출혈) | **{uf_dps:,.0f}** |")
print(f"| **특수기 우선 (Spec-First)** | Spec(치확/출혈) -> Ult(공버프) | {sf_dps:,.0f} |")
print(f"\n**차이**: 궁극기 우선 사이클이 특수기 우선 대비 **{diff:+.2f}%** 효율적입니다.")

print("\n### 분석 요약")
print("1. **공격력 버프의 가치**: 유미나는 기본 계수가 높고 패시브로도 공격력이 증가하기 때문에, 가장 강력한 스킬인 특수기(1.90) 사용 시점에 공격력 버프(+30%)가 이미 걸려 있는 '궁극기 우선' 사이클이 더 유리합니다.")
print("2. **치명타 버프 중첩**: 궁극기 우선 사이클에서도 2회차 행동(특수기) 시점에 공버프와 치확버프가 모두 중첩되므로, 딜 몰아주기 효율이 높습니다.")
