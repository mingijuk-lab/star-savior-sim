# -*- coding: utf-8 -*-
import codecs

fp = r'd:\Star\Core\calc_engine_v5.py'
with codecs.open(fp, 'r', 'utf-8') as f:
    lines = f.read().splitlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.strip()

    # 1. Attribute Mapping
    if stripped == 'attr_stack = 0':
        new_lines.append(line)
        new_lines.append('    c_attr = cdata.get("속성", "별")')
        new_lines.append('    if c_attr == "혼돈": attr_stack_name = "격동"')
        new_lines.append('    elif c_attr == "달": attr_stack_name = "냉각"')
        new_lines.append('    elif c_attr == "질서": attr_stack_name = "통찰"')
        new_lines.append('    elif c_attr == "태양": attr_stack_name = "점화"')
        new_lines.append('    else: attr_stack_name = "도약"')
        i += 1
        continue

    # 2. cr_from_buff remove
    if 'cr_from_buff = 0.30 if (is_frey and frey_cr_turns > 0)' in stripped:
        i += 1
        continue

    # 3. common_buffs array
    if stripped == 'target_def_base = 3000.0':
        new_lines.append('        # --- Common Buffs System (v4.0) ---')
        new_lines.append('        common_buffs = {')
        new_lines.append('            "atk": t.get("atk_buf", 0.0),')
        new_lines.append('            "def_red": max(t.get("def_red_buf", 0.0), 0.30 if smile_def_red_turns > 0 else 0.0),')
        new_lines.append('            "cr": t.get("cr_buf", 0.0),')
        new_lines.append('            "cd": t.get("cd_buf", 0.0)')
        new_lines.append('        }')
        new_lines.append('')
        new_lines.append(line)
        # Skip next two legacy Def Red check 
        i += 3
        new_lines.append('        current_def_red = common_buffs["def_red"]')
        continue

    # 4. Atk Buff
    if stripped == 'if lin_atk_buff_turns > 0:' and i+1 < len(lines) and 'dyn_atk_p_sum += 0.30' in lines[i+1]:
        new_lines.append(line)
        new_lines.append('                common_buffs["atk"] = max(common_buffs["atk"], 0.30)')
        i += 2
        continue

    if stripped == '# Collect DI and Buffs from turn data':
        if 'Cheongpung' in '\n'.join(new_lines[-5:]):
            new_lines.append('        dyn_atk_p_sum += common_buffs["atk"]')
            new_lines.append('            ')
            new_lines.append(line)
            i += 1
            continue

    # 5. Crit Buff
    if stripped == 'final_cr = char.get_stat(StatType.CRIT_RATE, []) + t.get("cr_buf", 0) + cr_from_buff':
        new_lines.append('        if is_frey and frey_cr_turns > 0:')
        new_lines.append('            common_buffs["cr"] = max(common_buffs["cr"], 0.30)')
        new_lines.append('            ')
        new_lines.append('        final_cr = char.get_stat(StatType.CRIT_RATE, []) + common_buffs["cr"]')
        i += 1
        continue

    if stripped == 'final_cd = char.get_stat(StatType.CRIT_DAMAGE, []) + t.get("cd_buf", 0) + caster_cd_stack * 0.10':
        new_lines.append('        final_cd = char.get_stat(StatType.CRIT_DAMAGE, []) + common_buffs["cd"] + caster_cd_stack * 0.10')
        i += 1
        continue

    new_lines.append(line)
    i += 1

with codecs.open(fp, 'w', 'utf-8') as f:
    f.write('\n'.join(new_lines) + '\n')

print("File updated directly via script without regex failures.")
