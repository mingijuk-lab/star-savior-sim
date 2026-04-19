
import json
import os

md_path = "Data/사이클_로테이션_마스터.md"

with open(md_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the end of markdown and start of JSON
json_start_line = -1
for i, line in enumerate(lines):
    if "<details>" in line:
        json_start_line = i
        break

if json_start_line == -1:
    print("Could not find JSON block start")
    exit(1)

# Prepare Markdown content
omega_md = """
---

## 오메가

- **사이클 길이**: 48 액션
- **궁극기 횟수**: 16
- **특수기 횟수**: 16

| 순서 | 행동 | 계수 | DI | ATK | CR | CD | SPD | 비고 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| T1 | U | 0.90 | 0.28 | 0.00 | 0.00 | 0.00 | 1.00 | U |
| T2 | S | 1.20 | 0.25 | 0.00 | 0.00 | 0.00 | 1.00 | S |
| T3 | B | 0.65 | 0.28 | 0.00 | 0.00 | 0.00 | 1.00 | B |
| T4 | U | 0.90 | 0.28 | 0.00 | 0.00 | 0.00 | 1.00 | U |
| T5 | S | 1.20 | 0.25 | 0.00 | 0.00 | 0.00 | 1.00 | S |
| T6 | B | 0.65 | 0.28 | 0.00 | 0.00 | 0.00 | 1.00 | B |
| ... | ... | ... | ... | ... | ... | ... | ... | (U-S-B 루프 반복) |

"""

# Prepare JSON data for Omega
def generate_omega_turns(n=48):
    turns = []
    for i in range(1, n + 1):
        mod = i % 3
        if mod == 1: # U
            turns.append({
                "coeff": 0.9, "di": 0.28, "atk_buf": 0.0, "cr_buf": 0.0, "cd_buf": 0.0,
                "def_pen_buf": 0.0, "spd_mult": 1.0, "is_ult": True, "is_basic": False, "note": f"T{i} U"
            })
        elif mod == 2: # S
            turns.append({
                "coeff": 1.2, "di": 0.25, "atk_buf": 0.0, "cr_buf": 0.0, "cd_buf": 0.0,
                "def_pen_buf": 0.0, "spd_mult": 1.0, "is_ult": False, "is_basic": False, "note": f"T{i} S"
            })
        else: # B
            turns.append({
                "coeff": 0.65, "di": 0.28, "atk_buf": 0.0, "cr_buf": 0.0, "cd_buf": 0.0,
                "def_pen_buf": 0.0, "spd_mult": 1.0, "is_ult": False, "is_basic": True, "note": f"T{i} B"
            })
    return turns

omega_json_data = {
    "cycle_length": 48,
    "turns": generate_omega_turns(48)
}

# Find the closing brace of the main JSON object
# The file ends with:
# ```json
# { ... }
# ```
# </details>
# ---

# We need to extract the existing JSON, add Omega, and write it back.
json_content_lines = []
in_json_block = False
json_start_idx = -1
json_end_idx = -1

for i in range(json_start_line, len(lines)):
    if "```json" in lines[i]:
        in_json_block = True
        json_start_idx = i + 1
        continue
    if "```" in lines[i] and in_json_block:
        json_end_idx = i
        break
    if in_json_block:
        json_content_lines.append(lines[i])

json_str = "".join(json_content_lines)
try:
    full_data = json.loads(json_str)
except Exception as e:
    print(f"Error parsing JSON: {e}")
    # Try a more robust way if it fails (maybe comments or something in the file)
    full_data = {}

full_data["오메가"] = omega_json_data
# For the variant "오메가(별속성파티)", we use the same rotation
full_data["오메가(별속성파티)"] = omega_json_data

# Merge everything back
new_lines = lines[:json_start_line]
new_lines.append(omega_md)
new_lines.append(lines[json_start_line]) # <details>
new_lines.append(lines[json_start_line+1]) # <summary>
new_lines.append(lines[json_start_line+2]) # empty line
new_lines.append("```json\n")
new_lines.append(json.dumps(full_data, ensure_ascii=False, indent=2))
new_lines.append("\n```\n")
new_lines.append("</details>\n")
new_lines.append("---\n")

with open(md_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Successfully updated rotation MD")
