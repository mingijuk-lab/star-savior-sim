import json
import re

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

def analyze_yumina_bleed(journey_type="AX", spec_max_stacks=2):
    specs = extract_json_from_md("d:/Star/Data/캐릭터_스펙_마스터.md")
    rotations = extract_json_from_md("d:/Star/Data/사이클_로테이션_마스터.md")
    
    cname = "유미나"
    cdata = specs[cname]
    rdata = rotations[cname]
    turns = rdata["turns"]
    
    yumina_stack = 0
    max_yumina_stack = cdata.get("패시브", {}).get("최대_스택", 5)
    
    bleeding_dots = []
    history = []
    MAX_ACTIONS = 20
    
    for i in range(MAX_ACTIONS):
        t = turns[i % len(turns)]
        is_ult = t.get("is_ult", False)
        is_basic = t.get("is_basic", False)
        is_spec = (not is_basic) and (not is_ult) and t.get("coeff", 0) > 0
        
        if journey_type == "GX" and is_basic:
            bleeding_dots.append({"turns": 2, "stacks": 0.5})
            
        m_bleed_count = 0
        if is_ult:
            m_bleed_count = 2
        elif is_spec:
            m_bleed_count = spec_max_stacks if yumina_stack >= 5 else 1
            
        if m_bleed_count > 0:
            bleeding_dots.append({"turns": 2, "stacks": m_bleed_count})
            
        current_stacks = sum(d["stacks"] for d in bleeding_dots)
        yumina_stack = min(yumina_stack + 1, max_yumina_stack)
        
        history.append({
            "action": i + 1,
            "bleed_stacks": current_stacks
        })
        
        for dot in bleeding_dots:
            dot["turns"] -= 1
        bleeding_dots = [d for d in bleeding_dots if d["turns"] > 0]

    steady_state = history[10:]
    avg = sum(h["bleed_stacks"] for h in steady_state) / len(steady_state)
    uptime = sum(1 for h in steady_state if h["bleed_stacks"] > 0) / len(steady_state) * 100
    return avg, uptime

print("### Yumina Bleed Comparison (Steady State) ###")
print("| Journey | Spec Max Stacks | Avg Stacks | Uptime (%) | Note |")
print("| :--- | :--- | :--- | :--- | :--- |")

# Current Code
avg, uptime = analyze_yumina_bleed("AX", 2)
print(f"| AX | 2 (Current) | {avg:.2f} | {uptime:.1f}% | Standard build |")

# Intended V8?
avg, uptime = analyze_yumina_bleed("AX", 3)
print(f"| AX | 3 (V8 Doc?) | {avg:.2f} | {uptime:.1f}% | Based on V8 doc example (1+2=3) |")

# GX Journey
avg, uptime = analyze_yumina_bleed("GX", 2)
print(f"| GX | 2 (Current) | {avg:.2f} | {uptime:.1f}% | Bleed-focus build |")

avg, uptime = analyze_yumina_bleed("GX", 3)
print(f"| GX | 3 (V8 Doc?) | {avg:.2f} | {uptime:.1f}% | Bleed-focus build |")
