import codecs, re

fp = r'd:\Star\Core\calc_engine_v5.py'
with codecs.open(fp, 'r', 'utf-8') as f:
    text = f.read()

# 1. Attribute Mapping
text = re.sub(
    r'([ \t]+# Universal Attribute \(속성\) Stack\r?\n[ \t]+attr_stack = 0)\r?\n([ \t]+# Rosaria Ignition)',
    r'\1\n    c_attr = cdata.get("속성", "별")\n    if c_attr == "혼돈": attr_stack_name = "격동"\n    elif c_attr == "달": attr_stack_name = "냉각"\n    elif c_attr == "질서": attr_stack_name = "통찰"\n    elif c_attr == "태양": attr_stack_name = "점화"\n    else: attr_stack_name = "도약"\n\2',
    text
)

# 2. cr_from_buff remove
text = re.sub(
    r'[ \t]+# Buff Application.*?cr_from_buff = 0\.30 if \(is_frey and frey_cr_turns > 0\) else 0\.0\r?\n',
    r'',
    text,
    flags=re.DOTALL
)

# 3. common_buffs
target_defense = r'([ \t]+)# 0\. Defense Calculation \(v14\.2\)\r?\n[ \t]+target_def_base = 3000\.0\r?\n[ \t]+# Check for DEF Reduction \(Smile\'s debuff or Journey\)\r?\n[ \t]+current_def_red = 0\.30 if smile_def_red_turns > 0 else 0\.0'
replacement_defense = r'\1# --- Common Buffs System (v4.0) ---\n\1common_buffs = {\n\1    "atk": t.get("atk_buf", 0.0),\n\1    "def_red": max(t.get("def_red_buf", 0.0), 0.30 if smile_def_red_turns > 0 else 0.0),\n\1    "cr": t.get("cr_buf", 0.0),\n\1    "cd": t.get("cd_buf", 0.0)\n\1}\n\n\1# 0. Defense Calculation (v14.2)\n\1target_def_base = 3000.0\n\1current_def_red = common_buffs["def_red"]'
text = re.sub(target_defense, replacement_defense, text)

# 4. Atk generic
target_atk = r'([ \t]+)if lin_atk_buff_turns > 0:\r?\n[ \t]+dyn_atk_p_sum \+= 0\.30\r?\n([ \t]+)# Cheongpung \(청풍\) SPD handled in spd_mult or final_spd\r?\n[ \t]+# Collect DI and Buffs from turn data'
replacement_atk = r'\1if lin_atk_buff_turns > 0:\n\1    common_buffs["atk"] = max(common_buffs["atk"], 0.30)\n\2# Cheongpung (청풍) SPD handled in spd_mult or final_spd\n\2\n\2# Add non-stacking Common ATK Buff\n\2dyn_atk_p_sum += common_buffs["atk"]\n\2\n\2# Collect DI and Buffs from turn data'
text = re.sub(target_atk, replacement_atk, text)

# 5. Crit
target_crit = r'([ \t]+)# Final Crit/CD Calculation including Passives \(v15\.0\)\r?\n[ \t]+final_cr = char\.get_stat\(StatType\.CRIT_RATE, \[\]\) \+ t\.get\("cr_buf", 0\) \+ cr_from_buff([^\n]+)\r?\n[ \t]+if any\(j\.name == "깊은 애도" for j in jrs\): final_cr \+= ra_cr_stack \* 0\.05\r?\n[ \t]+final_cd = char\.get_stat\(StatType\.CRIT_DAMAGE, \[\]\) \+ t\.get\("cd_buf", 0\) \+ caster_cd_stack \* 0\.10'
replacement_crit = r'\1# Final Crit/CD Calculation including Passives (v15.0)\n\1if is_frey and frey_cr_turns > 0:\n\1    common_buffs["cr"] = max(common_buffs["cr"], 0.30)\n\1    \n\1final_cr = char.get_stat(StatType.CRIT_RATE, []) + common_buffs["cr"]\2\n\1if any(j.name == "깊은 애도" for j in jrs): final_cr += ra_cr_stack * 0.05\n\1\n\1final_cd = char.get_stat(StatType.CRIT_DAMAGE, []) + common_buffs["cd"] + caster_cd_stack * 0.10'
text = re.sub(target_crit, replacement_crit, text)

with codecs.open(fp, 'w', 'utf-8') as f:
    f.write(text)

print("Engine refactored successfully.")
