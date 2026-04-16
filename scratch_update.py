import codecs
fp = r'd:\Star\Core\calc_engine_v5.py'
with codecs.open(fp, 'r', 'utf-8') as f:
    text = f.read()

# 1. Attribute Mapping
t1 = '''    # Universal Attribute (속성) Stack
    attr_stack = 0'''
r1 = '''    # Universal Attribute (속성) Stack
    attr_stack = 0
    c_attr = cdata.get("속성", "별")
    if c_attr == "혼돈": attr_stack_name = "격동"
    elif c_attr == "달": attr_stack_name = "냉각"
    elif c_attr == "질서": attr_stack_name = "통찰"
    elif c_attr == "태양": attr_stack_name = "점화"
    else: attr_stack_name = "도약"'''
text = text.replace(t1, r1)

# 2. cr_from_buff remove
t2 = '''        # Buff Application (Starts after Spec, so if it was set in PREVIOUS end-of-turn, it's active now)
        cr_from_buff = 0.30 if (is_frey and frey_cr_turns > 0) else 0.0
            
        # Stacking logic for specialized Journeys'''
r2 = '''        # Stacking logic for specialized Journeys'''
text = text.replace(t2, r2)

# 3. common_buffs
t3 = '''        # 0. Defense Calculation (v14.2)
        target_def_base = 3000.0
        # Check for DEF Reduction (Smile's debuff or Journey)
        current_def_red = 0.30 if smile_def_red_turns > 0 else 0.0
        
        # DEF Penetration (stat-based + dynamic buffer)
        def_pen_total = char.get_stat(StatType.DEF_PEN, []) + t.get("def_pen_buf", 0.0)'''
r3 = '''        # --- Common Buffs System (v4.0) ---
        common_buffs = {
            "atk": t.get("atk_buf", 0.0),
            "def_red": max(t.get("def_red_buf", 0.0), 0.30 if smile_def_red_turns > 0 else 0.0),
            "cr": t.get("cr_buf", 0.0),
            "cd": t.get("cd_buf", 0.0)
        }

        # 0. Defense Calculation (v14.2)
        target_def_base = 3000.0
        current_def_red = common_buffs["def_red"]
        
        # DEF Penetration (stat-based + dynamic buffer)
        def_pen_total = char.get_stat(StatType.DEF_PEN, []) + t.get("def_pen_buf", 0.0)'''
text = text.replace(t3, r3)

# 4. atk
t4 = '''            # Bright Moon (명월) ATK +20%
            if lin_bright_moon_turns > 0:
                dyn_atk_p_sum += 0.20
            if lin_atk_buff_turns > 0:
                dyn_atk_p_sum += 0.30
            # Cheongpung (청풍) SPD handled in spd_mult or final_spd
            
        # Collect DI and Buffs from turn data
        for k, v in t.items():
            if k.endswith("_di"): m_di += v
            if k.endswith("_atk_p"): dyn_atk_p_sum += v'''
r4 = '''            # Bright Moon (명월) ATK +20% (Unique Buff)
            if lin_bright_moon_turns > 0:
                dyn_atk_p_sum += 0.20
            if lin_atk_buff_turns > 0:
                common_buffs["atk"] = max(common_buffs["atk"], 0.30)
            # Cheongpung (청풍) SPD handled in spd_mult or final_spd
            
        dyn_atk_p_sum += common_buffs["atk"]
            
        # Collect DI and Buffs from turn data
        for k, v in t.items():
            if k.endswith("_di"): m_di += v
            if k.endswith("_atk_p"): dyn_atk_p_sum += v'''
text = text.replace(t4, r4)

# 5. crit
t5 = '''        # Final Crit/CD Calculation including Passives (v15.0)
        final_cr = char.get_stat(StatType.CRIT_RATE, []) + t.get("cr_buf", 0) + cr_from_buff
        if "클레어(바니걸)" in cname: final_cr += p_stacks["claire_cr"] * 0.10
        if any(j.name == "깊은 애도" for j in jrs): final_cr += ra_cr_stack * 0.05
        
        final_cd = char.get_stat(StatType.CRIT_DAMAGE, []) + t.get("cd_buf", 0) + caster_cd_stack * 0.10'''
r5 = '''        # Final Crit/CD Calculation including Passives (v15.0)
        if is_frey and frey_cr_turns > 0:
            common_buffs["cr"] = max(common_buffs["cr"], 0.30)
            
        final_cr = char.get_stat(StatType.CRIT_RATE, []) + common_buffs["cr"]
        if "클레어(바니걸)" in cname: final_cr += p_stacks["claire_cr"] * 0.10
        if any(j.name == "깊은 애도" for j in jrs): final_cr += ra_cr_stack * 0.05
        
        final_cd = char.get_stat(StatType.CRIT_DAMAGE, []) + common_buffs["cd"] + caster_cd_stack * 0.10'''
text = text.replace(t5, r5)

print("T1:", t1 not in text and r1 in text)
print("T3:", r3 in text)
print("T4:", r4 in text)
print("T5:", r5 in text)

with codecs.open(fp, 'w', 'utf-8') as f:
    f.write(text)
