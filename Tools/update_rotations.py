import json
import re
import os
from typing import Dict, List, Any

# Simple deep merge for strings, numbers and list
def deep_merge(base, update):
    if not isinstance(base, dict) or not isinstance(update, dict):
        return update
    for k, v in update.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base

def extract_json_from_md(filepath: str) -> Dict:
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    json_blocks = re.findall(r'```json\s+(.*?)\s+```', content, re.DOTALL)
    parsed_data = {}
    for block in json_blocks:
        try:
            # Handle math expressions like 1.525+0.15
            block = re.sub(r'([0-9.]+)\+([0-9.]+)', lambda m: str(float(m.group(1)) + float(m.group(2))), block)
            if block.strip().startswith('"'):
                data = json.loads("{" + block + "}")
            else:
                data = json.loads(block)
            
            if "이름" in data:
                cname = data["이름"]
                if cname not in parsed_data:
                    parsed_data[cname] = data
                else:
                    deep_merge(parsed_data[cname], data)
            else:
                # Top level objects without name
                deep_merge(parsed_data, data)
        except:
            continue
    return parsed_data

def generate_rotation(cname: str, cdata: Dict, max_turns=50) -> Dict:
    skills = cdata.get("스킬", {})
    u_spec = skills.get("궁극기", {})
    s_spec = skills.get("특수기", {})
    b_spec = skills.get("기본기", {})
    
    u_cd_max = u_spec.get("쿨타임", 5)
    s_cd_max = s_spec.get("쿨타임", 3)
    
    new_turns = []
    # State
    u_cd_rem, s_cd_rem = 0, 0
    attr_stack = 0 
    rosaria_upwa = 0 
    cooling_stack = 0
    hr_stack = 0
    yumina_hit_stack = 0
    charles_lucky_token = 0
    active_buffs = [] 

    t_idx = 1
    while t_idx <= max_turns:
        # Action Selection Priority
        has_extra_turn_s = ("추가 턴" in s_spec.get("부가", "") or "TN+1" in s_spec.get("부가", ""))
        
        # New Rule: If Ultimate has a Cooldown Reset on Max Stacks (Charles), 
        # only use it at 5 stacks to maximize efficiency.
        u_desc = u_spec.get("부가", "")
        is_reset_ult = ("초기화" in u_desc or "Reset" in u_desc)
        can_use_u = (u_cd_rem <= 0)
        if is_reset_ult and can_use_u and attr_stack < 5:
            can_use_u = False # Save for 5 stacks
        
        action_type = "B"
        if has_extra_turn_s and s_cd_rem <= 0:
            action_type = "S"
            spec = s_spec
            s_cd_rem = s_cd_max
        elif can_use_u:
            action_type = "U"
            spec = u_spec
            u_cd_rem = u_cd_max
        elif s_cd_rem <= 0:
            action_type = "S"
            spec = s_spec
            s_cd_rem = s_cd_max
        else:
            action_type = "B"
            spec = b_spec
            
        # 3. Handle Proactive Buffs (Buffs from the skill itself)
        부가 = spec.get("부가", "")
        # Duration Extraction
        dur_match = re.search(r"\((\d+)턴\)", 부가)
        duration = int(dur_match.group(1)) if dur_match else 2
        
        # Immediate extraction to apply to CURRENT turn if proactive
        # (Assuming most self-buffs apply before the damage event)
        current_skill_buffs = []
        atk_match = re.search(r"공(?:격력)?\s*[\+\-]?\s*(\d+)%", 부가)
        if atk_match: current_skill_buffs.append({"type": "atk", "value": int(atk_match.group(1))/100.0, "rem": duration})
        cr_match = re.search(r"치(?:명타\s*)?확(?:률)?\s*[\+\-]?\s*(\d+)%", 부가)
        if cr_match: current_skill_buffs.append({"type": "cr", "value": int(cr_match.group(1))/100.0, "rem": duration})
        cd_match = re.search(r"치(?:명타\s*)?피(?:해)?\s*[\+\-]?\s*(\d+)%", 부가)
        if cd_match: current_skill_buffs.append({"type": "cd", "value": int(cd_match.group(1))/100.0, "rem": duration})
        spd_match = re.search(r"속(?:도)?\s*[\+\-]?\s*(\d+)%", 부가)
        if spd_match: current_skill_buffs.append({"type": "spd", "value": 1.0 + int(spd_match.group(1))/100.0, "rem": duration})
        def_pen_match = re.search(r"방(?:어력)?\s*관(?:통)?\s*[\+\-]?\s*(\d+)%", 부가)
        if def_pen_match: current_skill_buffs.append({"type": "def_pen", "value": int(def_pen_match.group(1))/100.0, "rem": duration})

        # 4. Construction of the turn
        t = {
            "coeff": float(spec.get("계수", 1.5)),
            "di": float(spec.get("피해량_증가", 0.15)),
            "atk_buf": 0.0, "cr_buf": 0.0, "cd_buf": 0.0, "def_pen_buf": 0.0, "spd_mult": 1.0,
            "is_ult": (action_type == "U"),
            "is_basic": (action_type == "B")
        }
        
        # 5. Apply Active Buffs (EXCLUDING current skill buffs per user correction)
        for b in active_buffs:
            if b["rem"] <= 0: continue
            if b.get("filter") == "basic" and not (action_type.startswith("B") or t.get("is_basic")):
                continue
            if b["type"] == "atk": t["atk_buf"] = max(t["atk_buf"], b["value"])
            elif b["type"] == "spd": t["spd_mult"] = max(t["spd_mult"], b["value"])
            elif b["type"] == "cr": t["cr_buf"] = max(t["cr_buf"], b["value"])
            elif b["type"] == "cd": t["cd_buf"] = max(t["cd_buf"], b["value"])
            elif b["type"] == "di": t["di"] += b["value"]
            elif b["type"] == "def_pen": t["def_pen_buf"] = max(t["def_pen_buf"], b["value"])
            
        t["attribute_stack"] = cooling_stack if "프레이" in cname else attr_stack
        if "프레이" in cname: t["hr_stack"] = hr_stack
        if "로자리아" in cname: t["upwa_stack"] = round(rosaria_upwa, 2)
        if "유미나" in cname: t["yumina_hit_stack"] = yumina_hit_stack
        
        t["note"] = f"T{t_idx} {action_type}"
        new_turns.append(t)
        
        # 6. Commit Skill Buffs to persistent state (AFTER Turn addition)
        active_buffs.extend(current_skill_buffs)
        
        # 4. Trigger Stacks AFTER Action Logic
        if "로자리아" in cname:
            if action_type == "U":
                rosaria_upwa = min(rosaria_upwa + 3, 5)
            elif action_type == "S":
                trigger_extra = (rosaria_upwa >= 3)
                attr_stack = min(attr_stack + 1, 5)
                rosaria_upwa = 0
                if trigger_extra:
                    b_extra = t.copy()
                    b_extra.update({
                        "coeff": float(b_spec.get("계수", 1.50)),
                        "di": float(b_spec.get("피해량_증가", 0.15)),
                        "is_extra_attack": True, "note": f"T{t_idx}+ B_추가 (업화3+)",
                        "is_basic": True, "is_ult": False
                    })
                    for b in active_buffs:
                        if b["rem"] > 0 and b.get("filter") == "basic" and b["type"] == "di":
                            b_extra["di"] += b["value"]
                    new_turns.append(b_extra)
                    if attr_stack == 5: rosaria_upwa = min(rosaria_upwa + 1, 5)
            elif action_type == "B":
                attr_stack = min(attr_stack + 1, 5)
                rosaria_upwa = min(rosaria_upwa + (attr_stack * 0.20), 5.0)
        
        elif "클레어" in cname:
            if action_type == "B":
                attr_stack = min(attr_stack + 1, 5)
                if attr_stack == 5:
                    s_extra = t.copy()
                    s_extra.update({
                        "coeff": float(s_spec.get("계수", 1.55)),
                        "di": float(s_spec.get("피해량_증가", 0.15)),
                        "is_extra_attack": True, "note": f"T{t_idx}+ S_추가 (냉각5)",
                        "is_basic": False, "is_ult": False, "attribute_stack": 0
                    })
                    new_turns.append(s_extra)
                    attr_stack = 0
            elif action_type == "S": attr_stack = min(attr_stack + 3, 5)
        elif "유미나" in cname:
            if action_type == "B": 
                attr_stack = min(attr_stack + 1, 5)
                yumina_hit_stack = min(yumina_hit_stack + 1, 5)
            elif action_type == "U": 
                attr_stack = min(attr_stack + 2, 5)
        elif "프레이" in cname:
            if action_type == "S":
                cooling_stack = min(cooling_stack + 3, 5)
            elif action_type == "U":
                hr_stack = min(hr_stack + 3, 5)
            
            if "달속성파티" in cname:
                hr_stack = min(hr_stack + 1, 5) # Ally trigger approximation

            if action_type == "B":
                # Forced Negotiation triggers on HR >= 5
                if hr_stack >= 5:
                    t.update({
                        "coeff": 1.65,
                        "di": t["di"] + 1.00, # 강제 협상: +100% DI
                        "note": t["note"] + "_강제협상 (HR5)"
                    })
                    hr_stack = 0
                    t["ag_boost"] = 0.30
                else:
                    cooling_stack = min(cooling_stack + 1, 5)
        elif "샤를(바니걸)" in cname:
            if action_type == "S":
                attr_stack = min(attr_stack + 3, 5)
                charles_lucky_token = 3
            elif action_type == "U":
                if attr_stack >= 5: u_cd_rem = 0 # CDR Logic
                attr_stack = 0 # Reset stacks after consumption for Reset
            elif action_type == "B":
                attr_stack = min(attr_stack + 1, 5)
                if charles_lucky_token > 0:
                    b_extra = t.copy()
                    b_extra.update({
                        "coeff": float(b_spec.get("계수", 1.40)),
                        "is_extra_attack": True, "note": f"T{t_idx}+ B_추가 (럭키토큰)",
                        "is_basic": True, "is_ult": False
                    })
                    new_turns.append(b_extra)
        else:
            if action_type == "B": attr_stack = min(attr_stack + 1, 5)

        for b in active_buffs: b["rem"] -= 1
        charles_lucky_token -= 1

        부가 = spec.get("부가", "")
        # Robust Regex Detection for Buffs (ATK, CR, CD, SPD)
        # Supports: "+30%", "30% 증가", "(2턴)", "(3턴)"
        
        # Duration Extraction
        dur_match = re.search(r"\((\d+)턴\)", 부가)
        duration = int(dur_match.group(1)) if dur_match else 2
        
        # Modifier Extractions
        atk_match = re.search(r"공(?:격력)?\s*[\+\-]?\s*(\d+)%", 부가)
        if atk_match: active_buffs.append({"type": "atk", "value": int(atk_match.group(1))/100.0, "rem": duration})
        
        cr_match = re.search(r"치(?:명타\s*)?확(?:률)?\s*[\+\-]?\s*(\d+)%", 부가)
        if cr_match: active_buffs.append({"type": "cr", "value": int(cr_match.group(1))/100.0, "rem": duration})

        cd_match = re.search(r"치(?:명타\s*)?피(?:해)?\s*[\+\-]?\s*(\d+)%", 부가)
        if cd_match: active_buffs.append({"type": "cd", "value": int(cd_match.group(1))/100.0, "rem": duration})
        
        spd_match = re.search(r"속(?:도)?\s*[\+\-]?\s*(\d+)%", 부가)
        if spd_match: active_buffs.append({"type": "spd", "value": 1.0 + int(spd_match.group(1))/100.0, "rem": duration})
        
        def_pen_match = re.search(r"방(?:어력)?\s*관(?:통)?\s*[\+\-]?\s*(\d+)%", 부가)
        if def_pen_match: active_buffs.append({"type": "def_pen", "value": int(def_pen_match.group(1))/100.0, "rem": duration})
        
        if "추가 턴" in 부가 or "TN+1" in 부가: t["is_extra_turn"] = True

        if "로자리아" in cname and action_type == "U":
            t["note"] += " (행게+50%)"
            t["ag_boost"] = 0.50
            active_buffs.append({"type": "spd", "value": 1.15, "rem": 3})
            active_buffs.append({"type": "di", "value": 0.15, "rem": 3, "filter": "basic"})

        if "프레이" in cname and action_type == "B" and "Jackpot" in t.get("note", ""):
            t["ag_boost"] = 0.30

        u_cd_rem -= 1
        s_cd_rem -= 1
        t_idx += 1 # Extra Turns (TN+1) consume time in v14.1
        
    return {
        "cycle_length": len(new_turns),
        "turns": new_turns
    }

def main():
    if not os.path.exists("Data/characters.json"):
        print("Error: Data/characters.json not found. Run Tools/extract_characters.py first.")
        return

    with open("Data/characters.json", "r", encoding="utf-8") as f:
        specs = json.load(f)
    new_rotations = {}
    for cname, cdata in specs.items():
        new_rotations[cname] = generate_rotation(cname, cdata, 50)
    
    with open("Data/사이클_로테이션_마스터.md", "w", encoding="utf-8") as f:
        f.write("# 사이클 로테이션 마스터 (v14.1/v6)\n\n")
        f.write("> **설명**: 시뮬레이션 엔진이 참조하는 공인 로테이션 데이터입니다. 가독성을 위해 테이블 형식을 제공하며, 하단의 JSON 블록은 엔진 파싱용입니다.\n\n")
        
        # 1. Table of Contents
        f.write("## 📋 캐릭터 목차\n\n")
        for cname in sorted(new_rotations.keys()):
            f.write(f"- [{cname}](#{cname.replace('(', '').replace(')', '').replace(' ', '-')})\n")
        f.write("\n---\n\n")
        
        # 2. Per Character Section
        for cname in sorted(new_rotations.keys()):
            rot = new_rotations[cname]
            f.write(f"## {cname}\n\n")
            
            # Summary stats
            ult_count = sum(1 for t in rot["turns"] if t.get("is_ult"))
            spec_count = sum(1 for t in rot["turns"] if not t.get("is_ult") and not t.get("is_basic") and not t.get("is_extra_attack"))
            f.write(f"- **사이클 길이**: {rot['cycle_length']} 액션\n")
            f.write(f"- **궁극기 횟수**: {ult_count}\n")
            f.write(f"- **특수기 횟수**: {spec_count}\n\n")
            
            # Action Table (First 30 turns for brevity or all?)
            f.write("| 순서 | 행동 | 계수 | DI | ATK | CR | CD | SPD | 비고 |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for t in rot["turns"][:30]: # Show up to 30 turns for readability
                action = "ULT" if t.get("is_ult") else ("BASIC" if t.get("is_basic") else "SPEC")
                if t.get("is_extra_attack"): action = f"**{action}(+)**"
                
                f.write(f"| {t['note'].split()[0]} | {action} | {t['coeff']:.2f} | {t['di']:.2f} | {t['atk_buf']:.2f} | {t.get('cr_buf', 0.0):.2f} | {t.get('cd_buf', 0.0):.2f} | {t['spd_mult']:.2f} | {t['note'].split(' ', 1)[1] if ' ' in t['note'] else ''} |\n")
            
            if len(rot["turns"]) > 30:
                f.write(f"| ... | ... | ... | ... | ... | ... | (총 {len(rot['turns'])}턴 중 30턴까지 표시) |\n")
            
            f.write("\n<details>\n<summary>⚙️ 엔진 파싱용 JSON 데이터</summary>\n\n")
            f.write("```json\n")
            # Write only this character's block
            f.write(json.dumps({cname: rot}, indent=2, ensure_ascii=False))
            f.write("\n```\n")
            f.write("</details>\n\n---\n\n")
            
    print(f"Successfully updated Data/사이클_로테이션_마스터.md with formatted tables.")

if __name__ == "__main__":
    main()
