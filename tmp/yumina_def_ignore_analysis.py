import json
import re
import sys
import io

# Force stdout to use utf-8 to avoid mangling in some environments
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

def run_sim(journey_type="AX", bleed_ignores_def=False, def_rate=0.5):
    specs = extract_json_from_md("d:/Star/Data/캐릭터_스펙_마스터.md")
    rotations = extract_json_from_md("d:/Star/Data/사이클_로테이션_마스터.md")
    
    cname = "유미나"
    cdata = specs[cname]
    rdata = rotations[cname]
    turns = rdata["turns"]
    
    # Simple pool calculation (from calc_dps.py logic)
    pool = (cdata["기본_스탯"]["공격력"] + 1250) * (1 + cdata["공명"].get("퍼센트", 0)) + cdata["공명"].get("정수", 0)
    d_static = cdata["패시브"].get("공격력_퍼센트", 0) + 0.1625 + 0.01 + 0.06 + 0.08 # passive + equip_sub + research + arc_base + AX_base
    if journey_type == "GX": d_static -= 0.08 # No AX base
    
    # Equipment: Destruction (40% Crit Dmg)
    eq_atk = 0.0
    eq_cr = 0.0
    eq_cd = 0.40
    
    # Arcana: Yumina Exclusive (6% Atk, 24% CR, 12% CD)
    arc_atk = 0.06
    arc_cr = 0.24
    arc_cd = 0.12
    
    base_atk = cdata["기본_스탯"]["공격력"]
    base_spd = cdata["기본_스탯"].get("속도", 100)
    base_cr = cdata["기본_스탯"].get("치명타_확률", 0.05)
    base_cd = cdata["기본_스탯"].get("치명타_피해", 0.50)
    
    final_spd = base_spd + 60
    cr_total = base_cr + arc_cr + eq_cr + cdata["패시브"].get("치확_퍼센트", 0)
    cd_total = base_cd + arc_cd + eq_cd
    
    yumina_stack = 0
    ax_stack = 0
    bleeding_dots = []
    
    total_dmg = 0
    cycle_time = 0
    MAX_ACTIONS = 15
    
    for i in range(MAX_ACTIONS):
        t = turns[i % len(turns)]
        is_ult = t.get("is_ult", False)
        is_basic = t.get("is_basic", False)
        is_spec = (not is_basic) and (not is_ult) and t.get("coeff", 0) > 0
        
        # 1. Timing
        spd_i = final_spd * t.get("spd_mult", 1.0)
        cycle_time += 1000.0 / spd_i
        
        # 2. AX Stack
        if journey_type == "AX": ax_stack = min(ax_stack + 1, 5)
        
        # 3. Stats
        m_atk = min(yumina_stack * 0.04, 0.20)
        ax_val = (ax_stack * 0.08) if journey_type == "AX" else 0.0
        total_dyn_atk = t.get("atk_buf", 0) + m_atk + ax_val
        
        eff_base = pool * (1 + d_static) + 1000
        eff_atk = eff_base * (1 + total_dyn_atk)
        
        cr_i = min(cr_total + t.get("cr_buf", 0), 1.0)
        cd_i = cd_total + t.get("cd_buf", 0)
        crit_contrib = cr_i * cd_i
        
        # 4. Direct Damage
        turn_direct_dmg = 0
        coeff = t.get("coeff", 0)
        if coeff > 0:
            raw_dmg = (eff_atk * coeff) * (1 + t.get("di", 0) + crit_contrib)
            # Apply defense to direct damage
            turn_direct_dmg = raw_dmg * (1 - def_rate)
            
        # 5. Bleed Application
        if journey_type == "GX" and is_basic:
            bleeding_dots.append({"turns": 2, "atk": eff_atk * 0.5, "di": t.get("di", 0)})
            
        m_bleed_count = 0
        if is_ult: m_bleed_count = 2
        elif is_spec: m_bleed_count = 3 if yumina_stack >= 5 else 1 # Using V8 doc intended (3 stacks)
            
        if m_bleed_count > 0:
            bleeding_dots.append({"turns": 2, "atk": eff_atk * m_bleed_count, "di": t.get("di", 0)})
            
        # 6. Bleed Tick
        turn_bleed_dmg = 0
        for dot in bleeding_dots:
            raw_bleed = dot["atk"] * 0.25 * (1 + dot["di"])
            # Apply defense (or ignore)
            if bleed_ignores_def:
                turn_bleed_dmg += raw_bleed
            else:
                turn_bleed_dmg += raw_bleed * (1 - def_rate)
            dot["turns"] -= 1
        
        bleeding_dots = [d for d in bleeding_dots if d["turns"] > 0]
        
        total_dmg += turn_direct_dmg + turn_bleed_dmg
        yumina_stack = min(yumina_stack + 1, 5)
        if is_ult and journey_type == "AX": ax_stack = 0
        
    return total_dmg / cycle_time

print(f"### 유미나 방어 무시 영향 분석 (방어율 50% 기준) ###\n")
print("| 빌드 | 출혈 방어무시 미적용 DPS | 출혈 방어무시 적용 DPS | 상승률 |")
print("| :--- | :---: | :---: | :---: |")

ax_normal = run_sim("AX", False)
ax_ignore = run_sim("AX", True)
ax_up = (ax_ignore - ax_normal) / ax_normal * 100
print(f"| AX 여정 | {ax_normal:,.0f} | {ax_ignore:,.0f} | +{ax_up:.2f}% |")

gx_normal = run_sim("GX", False)
gx_ignore = run_sim("GX", True)
gx_up = (gx_ignore - gx_normal) / gx_normal * 100
print(f"| GX 여정 | {gx_normal:,.0f} | {gx_ignore:,.0f} | +{gx_up:.2f}% |")

print(f"\n**기존 AX 빌드가 GX 빌드보다 강력한 비율**: {(ax_normal / gx_normal - 1) * 100:.2f}% (방어 무시 미적용 시)")
print(f"**방어 무시 적용 시 효율 차이**: {(ax_ignore / gx_ignore - 1) * 100:.2f}% (AX가 여전히 강한지 확인)")
