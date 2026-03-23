import math

def simulate_frey_dmg(journey_type):
    # --- V8 Character Specs (Frey) ---
    pool = 5800
    base_cr = 0.05
    base_cd = 0.68
    passive_atk = 0.15 # Passive level 4
    
    # --- V6 Common Assumption ---
    b_stat = 1000 # 정수 합산
    tactical_atk = 0.01
    substat_atk = 0.1625
    
    # --- Arcana (Caster A assumed as standard for Frey) ---
    arc_atk = 0.14
    arc_cr = 0.30
    arc_cd_stack = 0.30 # Steady-state stack assumption from calc_dps.py
    
    # --- Equipment (Insight 4 set) ---
    eq_cr = 0.30
    
    # --- Journey AX/FX Stats ---
    jr_atk_base = 0.08 if journey_type == "AX" else 0.00
    jr_cd = 0.10 if journey_type == "FX" else 0.00
    
    # --- d_static calculation ---
    d_static = passive_atk + arc_atk + tactical_atk + substat_atk + jr_atk_base
    
    # Base effective atk (v6 formula)
    eff_base = pool * (1 + d_static) + b_stat
    
    # Crit stats
    cr_total = base_cr + arc_cr + eq_cr
    cd_total = base_cd + arc_cd_stack + jr_cd
    
    # --- Simulation State ---
    ax_stack = 0
    fx_carry = 0.0
    hr_stack = 0
    total_dmg = 0.0
    
    # ---------------------------------------------------------
    # Turn 1: Ult
    # ---------------------------------------------------------
    # 1. Turn Start journey update
    if journey_type == "AX":
        ax_stack = min(ax_stack + 1, 5)
        
    # 2. Skill use
    coeff = 1.40
    di = 0.15
    
    # 3. Stats for hit
    ax_val = (ax_stack * 0.08) if journey_type == "AX" else 0.0
    eff_atk = eff_base * (1 + ax_val)
    
    crit_contrib = cr_total * cd_total
    current_di = di + fx_carry
    
    # 4. Damage
    dmg_ult = (eff_atk * coeff) * (1 + current_di + crit_contrib)
    total_dmg += dmg_ult
    
    # 5. Post action
    hr_stack += 3
    if journey_type == "AX":
        ax_stack = 0 # Reset after Ult
    if journey_type == "FX":
        fx_carry = cr_total * 0.25 # Expected carry
        
    # ---------------------------------------------------------
    # Turn 2: Special
    # ---------------------------------------------------------
    # 1. Turn Start
    if journey_type == "AX":
        ax_stack = min(ax_stack + 1, 5)
        
    # 2. Skill use (Special)
    # Buffs: Crit+30% (3 turns)
    extra_cr = 0.30
    dmg_special = 0.0 # Coeff 0
    
    # 3. Post action
    # FX carry: "0% coeff is not a hit, doesn't consume/trigger carry"
    # Special has 0 coeff, so fx_carry remains from Ult.
    
    # ---------------------------------------------------------
    # Turn 2 Extra: Basic (from Special's Extra Turn)
    # ---------------------------------------------------------
    # 1. Turn Start journey update
    # Note: calc_dps.py increments for each element in rotation turns.
    # Extra Turn actions are separate elements.
    if journey_type == "AX":
        ax_stack = min(ax_stack + 1, 5)
        
    # 2. Skill use
    coeff_basic = 1.65
    di_basic = 0.15 + (hr_stack * 0.01) # Basic DI + HR DI
    
    # 3. Stats for hit
    ax_val = (ax_stack * 0.08) if journey_type == "AX" else 0.0
    eff_atk = eff_base * (1 + ax_val)
    
    cr_action = min(cr_total + extra_cr, 1.0)
    crit_contrib_action = cr_action * cd_total
    current_di_action = di_basic + fx_carry
    
    # 4. Damage
    dmg_basic = (eff_atk * coeff_basic) * (1 + current_di_action + crit_contrib_action)
    total_dmg += dmg_basic
    
    return dmg_ult, dmg_basic, total_dmg

# Executing simulation
ax_ult, ax_basic, ax_total = simulate_frey_dmg("AX")
fx_ult, fx_basic, fx_total = simulate_frey_dmg("FX")

print("### [V8/V6] Frey Journeys (AX vs FX) Comparison (First 2 Turns) ###")
print(f"**Scenario**: Turn 1 (Ultimate) -> Turn 2 (Special -> Extra Basic)\n")
print(f"| Metric | Journey AX | Journey FX | Difference |")
print(f"| :--- | :--- | :--- | :--- |")
print(f"| Ult Damage | {ax_ult:,.0f} | {fx_ult:,.0f} | {ax_ult-fx_ult:+,.0f} |")
print(f"| Basic Damage | {ax_basic:,.0f} | {fx_basic:,.0f} | {ax_basic-fx_basic:+,.0f} |")
print(f"| **Total Damage** | **{ax_total:,.0f}** | **{fx_total:,.0f}** | **{ax_total-fx_total:+,.0f} ({((ax_total-fx_total)/fx_total)*100:+.2f}%)** |")
