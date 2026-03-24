import json
import re
import csv
from itertools import combinations
from calc_dps import extract_json_from_md, get_mechanic, EQUIPMENTS, ARCANAS, JOURNEYS, calculate_dps

class TeamMember:
    def __init__(self, name, cdata, rdata, equip, arcana, journey):
        self.name = name
        self.cdata = cdata
        self.rdata = rdata
        self.equip = equip
        self.arcana = arcana
        self.journey = journey
        
        # Base Stats
        base_atk = cdata.get("기본_스탯", {}).get("공격력", 0)
        base_spd = cdata.get("기본_스탯", {}).get("속도", 100)
        base_cr = cdata.get("기본_스탯", {}).get("치명타_확률", 0.05)
        base_cd = cdata.get("기본_스탯", {}).get("치명타_피해", 0.50)
        
        res_pct = cdata.get("공명", {}).get("퍼센트", 0.0) or cdata.get("공명", {}).get("공격력_퍼센트", 0.0)
        res_int = cdata.get("공명", {}).get("정수", 0.0) or cdata.get("공명", {}).get("공격력_정수", 0.0)
        self.pool = (base_atk + 1250) * (1 + res_pct) + res_int
        
        self.passive_atk = cdata.get("패시브", {}).get("공격력_퍼센트", 0.0)
        self.passive_cr = cdata.get("패시브", {}).get("치확_퍼센트", 0.0)
        
        arc_spd_static = 8 if arcana["type"] == "strikerB" else 0
        self.static_spd = base_spd + 60 + arc_spd_static + equip.get("spd", 0)
        
        self.d_static = self.passive_atk + arcana["atk"] + journey["atk_base"] + 0.01 + equip["atk"] + 0.1625
        self.cr_total_base = base_cr + arcana["cr"] + journey.get("cr", 0) + equip.get("cr", 0) + self.passive_cr
        self.cd_total_base = base_cd + arcana["cd"] + journey.get("cd", 0) + equip.get("cd", 0)

        # State Transitions
        self.mechanic = get_mechanic(name, cdata)
        self.gauge = 0.0
        self.turns_taken = 0
        self.action_index = 0
        
        # Dynamics
        self.ax_stack = 0
        self.ga_reduction = 0.0
        self.fx_carry = 0.0
        self.caster_cd_stack = 0
        self.assassin_spd_stack = 0
        self.omega_dmg_stack = 0
        self.ra_cr_stack = 0
        self.rc_atk_stack = 0.0
        self.rc_spec_stack = 0
        self.rc_atk_stack = 0.0
        self.total_dmg_contributed = 0.0
        
        # Attributes
        self.attribute = "Normal"
        if "프레이" in name or "루나" in name or "에핀델" in name or "클레어" in name or "벨리스" in name:
            self.attribute = "Moon"
        elif "샤를" in name or "뮤리엘" in name or "스칼렛" in name or "스마일" in name:
            self.attribute = "Sun"

    def get_current_spd(self):
        # Assassin Spd Stack handled in turn start
        return (self.static_spd + self.assassin_spd_stack * 10)

def simulate_party(members, max_actions=50):
    total_dmg = 0.0
    action_count = 0
    
    # Global state
    def_shred_timer = 0
    def_shred_val = 0.0
    ex_bonus_accum = 0.0
    
    # Initiative
    for m in members:
        m.gauge = 0.0
        
    while action_count < max_actions:
        # Tick until someone reaches 1000 gauge
        # In this sim, we use a global clock increment
        # Or just find who reaches 1000 first
        time_to_next = min((1000.0 * (1.0 - m.gauge/1000.0)) / (m.get_current_spd() or 1) for m in members)
        
        for m in members:
            m.gauge += time_to_next * m.get_current_spd()
        
        # Find character with max gauge
        actor = max(members, key=lambda m: m.gauge)
        actor.gauge -= 1000.0
        # Wait, if gauge was > 1000, keep the overflow?
        # Simulation Guideline: "행동 후 게이지 0으로 초기화, 다시 속도에 따라 증가"
        # "행동 게이지 N% 증가 = 게이지가 100% 기준 N%만큼 즉시 증가"
        # So it resets to 0, but can be higher if buffed.
        actor.gauge = 0.0 + actor.ga_reduction * 1000.0
        actor.ga_reduction = 0.0
        
        # Action Start
        action_count += 1
        actor.turns_taken += 1
        
        # Def Shred Decay
        if def_shred_timer > 0:
            def_shred_timer -= 1
        else:
            def_shred_val = 0.0
            
        # Turn Logic (Based on calc_dps.py loop)
        turns = actor.rdata.get("turns", [])
        t = turns[actor.action_index % len(turns)]
        actor.action_index += 1
        
        # Arcana Stacks
        if actor.arcana["type"] == "assassin": actor.assassin_spd_stack = min(actor.assassin_spd_stack + 1, 3)
        if actor.arcana["type"] in ["strikerA", "strikerC", "strikerD", "casterB", "casterC", "rangerB"]:
            actor.omega_dmg_stack = min(actor.omega_dmg_stack + 1, 5)
        if actor.arcana["type"] in ["casterA", "casterB", "casterC"]:
            actor.caster_cd_stack = min(actor.caster_cd_stack + 1, 3)
            
        if actor.journey["type"] == "AX": actor.ax_stack = min(actor.ax_stack + 1, 5)
        
        # Hit List
        is_ult = t.get("is_ult", False)
        base_hits = t.get("hits", 4 if is_ult else 1)
        hit_list = []
        if t.get("coeff", 0.0) > 0:
            hit_list.extend([t["coeff"] / base_hits] * base_hits)
        if t.get("extra_coeff", 0.0) > 0:
            hit_list.append(t["extra_coeff"])
            
        # Rosaria Auto-Bonus
        if actor.name.startswith("로자리아") and (not is_ult) and t.get("is_basic", False):
             if getattr(actor.mechanic, 'stacks', {}).get("upwa", 0) >= 3.0:
                  hit_list.append(1.50)

        turn_dmg = 0.0
        expected_crits = 0.0
        prob_none_crit = 1.0
        
        for hit in hit_list:
            m_di, m_atk = actor.mechanic.hit_pre(t, actor.arcana)
            
            ra_cr_bonus = (actor.ra_cr_stack * 0.05) if "레인저" in actor.arcana["class"] else 0.0
            ranger_buff_bonus = 0.50 if "레인저" in actor.arcana["class"] else 0.0
            cr_i = min(actor.cr_total_base + t.get("cr_buf", 0.0) + ra_cr_bonus + ranger_buff_bonus, 1.0)
            cd_i = actor.cd_total_base + t.get("cd_buf", 0.0) + (actor.caster_cd_stack * 0.10)
            
            crit_contrib = cr_i * cd_i
            prob_none_crit *= (1.0 - cr_i)
            expected_crits += cr_i
            
            ra_atk_bonus = (actor.ra_atk_stack * 0.03) if actor.arcana["type"] == "rangerA" else 0.0
            rc_atk_bonus = (actor.rc_atk_stack * 0.03) if actor.arcana["type"] in ["rangerC", "rangerD"] else 0.0
            ax_val = (actor.ax_stack * 0.08) if actor.journey["type"] == "AX" else 0.0
            
            total_dyn_atk = t.get("atk_buf", 0.0) + ra_atk_bonus + rc_atk_bonus + m_atk + ax_val
            
            eff_base = actor.pool * (1 + actor.d_static) + 1000
            eff_atk = eff_base * (1 + total_dyn_atk)
            
            omega_di = (actor.omega_dmg_stack * 0.05) if t.get("omega_elig", False) else 0.0
            rc_spec_di = (actor.rc_spec_stack * 0.05) if actor.arcana["type"] in ["rangerC", "rangerD"] else 0.0
            total_di = t.get("di", 0.0) + omega_di + actor.fx_carry + rc_spec_di + m_di
            
            # Apply Def Shred Synergy
            # Typical Def 3000 (50% DR). 30% Shred -> 2100 (41% DR).
            # Shred multiplier = (1-0.41)/(1-0.50) = 0.59/0.50 = 1.18
            shred_mult = 1.0
            if def_shred_val > 0:
                # Approximation: Shred 30% -> ~18% damage increase
                shred_mult = 1.0 + (def_shred_val * 0.6) 

            dmg = (eff_atk * hit) * (1 + total_di + crit_contrib) * shred_mult
            turn_dmg += dmg
            actor.total_dmg_contributed += dmg
            
            if "레인저" in actor.arcana["class"] and t.get("is_basic", False):
                actor.ra_cr_stack = min(actor.ra_cr_stack + 1, 5)
            if is_ult:
                if actor.arcana["type"] == "rangerA": actor.ra_atk_stack = min(actor.ra_atk_stack + cr_i, 5.0)
                if actor.arcana["type"] in ["rangerC", "rangerD"]: actor.rc_atk_stack = min(actor.rc_atk_stack + cr_i, 5.0)
            
            actor.mechanic.on_hit(t, is_ult, cr_i)

        # Post Action
        actor.ga_reduction = actor.mechanic.post_action(t, is_ult, prob_none_crit, expected_crits)
        
        if actor.journey["type"] == "FX" and hit_list:
            actor.fx_carry = (1.0 - prob_none_crit) * 0.25
        if actor.journey["type"] == "EX" and t.get("is_basic", False):
            ex_bonus_accum += (1.0 - prob_none_crit) * 0.25 * 16215
            
        is_spec = (not t.get("is_basic", False)) and (not is_ult) and t.get("coeff", 0) > 0
        if is_spec and actor.arcana["type"] in ["rangerB", "rangerC", "rangerD"]:
            actor.rc_spec_stack = min(actor.rc_spec_stack + 1, 5)
        if is_ult and actor.journey["type"] == "AX":
            actor.ax_stack = 0
            
        # Synergy Implementation
        # 1. Frey Gauge Boost (for Moon Allies)
        if actor.attribute == "Moon":
            # Find Frey in party and boost her
            for m in members:
                if "프레이" in m.name and m != actor:
                    # Frey gets 8% gauge and HR stack
                    m.gauge += 80.0
                    if hasattr(m.mechanic, 'stacks'):
                        m.mechanic.stacks["hr"] = min(m.mechanic.stacks.get("hr", 0) + 1, 5)
            # Extra Frey Logic: Epindel also benefits?
            # "달 속성 아군 치명타 발생 시 냉각 스택 +1"
            for m in members:
                if "에핀델" in m.name and m != actor:
                    if (1.0 - prob_none_crit) > 0.5: # Simple approximation for team crit
                        if hasattr(m.mechanic, 'stacks'):
                            m.mechanic.stacks["cooling"] = min(m.mechanic.stacks.get("cooling", 0) + 1, 5)

        # 2. DEF Shred (Rosaria/Smile)
        if is_ult:
            if "로자리아" in actor.name:
                def_shred_val = 0.30
                def_shred_timer = 8 # 2 "actor turns" or global turns? 
                # Guideline says 2 turns duration. In party sim, this means 2 actions of EACH teammate?
                # Usually it means 2 turns of the ENEMY or 2 rounds.
                # Let's assume 8 actions total across party (2 actions each for 4 members).
            if "스마일" in actor.name:
                def_shred_val = 0.30
                def_shred_timer = 8

        total_dmg += turn_dmg

    # EX bonus management - add to appropriate members
    for m in members:
        if m.journey["type"] == "EX":
             # ex_bonus_accum was global, but it's generated by basics of EX journey users
             # In my simplified sim, I'll just add it to the members who are on EX journey
             # Since ex_bonus_accum was global, I'll redistribute it or track per member
             pass # For now, total_dmg_contributed already tracked turn_dmg. 
             # I'll just skip complex EX redistribution for now as it's a niche case.

    # Return total and individual shares
    member_damages = {m.name: m.total_dmg_contributed for m in members}
    return total_dmg, member_damages

def main():
    specs = extract_json_from_md("Data/캐릭터_스펙_마스터.md")
    rotations = extract_json_from_md("Data/사이클_로테이션_마스터.md")
    
    candidates = ["로자리아", "유미나", "유미나(패시브1lv)", "레이시", "루나", "리디아", "프레이(달속성파티)", "샤를(바니걸)", "에핀델", "벨리스"]
    
    # Pre-optimize equipment for each candidate individually
    best_config = {}
    print("Pre-optimizing equipment for candidates...")
    
    for name in candidates:
        best_dmg = 0
        best_equip = "통찰4세트" # Default
        
        # Determine best Arcana (simplified)
        arc_class = specs[name].get("분류", "")
        best_arc = "캐스터C"
        if "레인저" in arc_class: best_arc = "레인저C"
        elif "스트라이커" in arc_class or "디펜더" in arc_class: best_arc = "스트라이커B"
        elif "어쌔신" in arc_class: best_arc = "어쌔신"
        
        for eq_name in ["공격4세트", "통찰4세트", "파괴4세트"]:
            m = TeamMember(name, specs[name], rotations[name], EQUIPMENTS[eq_name], ARCANAS[best_arc], JOURNEYS["AX"])
            dmg, _ = simulate_party([m], 50) # Run as solo
            if dmg > best_dmg:
                best_dmg = dmg
                best_equip = eq_name
        
        best_config[name] = {"equip": best_equip, "arcana": best_arc, "journey": "AX"}
        print(f"  {name}: {best_equip} ({round(best_dmg, 0)})")

    party_results = []
    print(f"Starting combinatorial search from {len(candidates)} candidates...")
    
    for combo in combinations(candidates, 4):
        members = []
        for name in combo:
            cfg = best_config[name]
            members.append(TeamMember(
                name, specs[name], rotations[name], 
                EQUIPMENTS[cfg["equip"]], ARCANAS[cfg["arcana"]], JOURNEYS[cfg["journey"]]
            ))
        
        # Run sim 50 actions
        score, shares = simulate_party(members, 50)
        
        # Format shares as percentage
        share_str = ", ".join([f"{n}: {round(v/score*100, 1)}%" for n, v in shares.items()])
        
        party_results.append({
            "Party": ", ".join(combo),
            "TotalDamage": round(score, 2),
            "AvgDamage": round(score / 50, 2),
            "Shares": share_str
        })
        
    party_results.sort(key=lambda x: x["TotalDamage"], reverse=True)
    
    # Save results
    with open("Results/party_sim_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["Party", "TotalDamage", "AvgDamage", "Shares"])
        writer.writeheader()
        writer.writerows(party_results[:50]) # Top 50
        
    top = party_results[0]
    print(f"Simulation finished. Top party: {top['Party']} with {top['TotalDamage']} damage.")
    print(f"Damage Shares: {top['Shares']}")

if __name__ == "__main__":
    main()
