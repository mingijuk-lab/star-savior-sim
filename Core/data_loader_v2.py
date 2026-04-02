import json
import re
# import pandas as pd (Moved inside functions requiring it to optimize PyScript)
from typing import Dict, List
from Core.models_v2 import EquipmentPiece, EquipmentSet, Modifier, StatType, ModifierType, Arcana, Journey

def extract_json_from_md(filepath: str) -> Dict:
    """Extracts all JSON blocks from a markdown file and merges them."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    json_blocks = re.findall(r'```json\s+(.*?)\s+```', content, re.DOTALL)
    parsed_data = {}
    for block in json_blocks:
        try:
            # Handle basic arithmetic like "3614+1250"
            block = re.sub(r'([0-9.]+)\+([0-9.]+)', lambda m: str(float(m.group(1)) + float(m.group(2))), block)
            if block.strip().startswith('"'):
                data = json.loads("{" + block + "}")
                parsed_data.update(data)
            else:
                data = json.loads(block)
                if "이름" in data:
                    parsed_data[data["이름"]] = data
                else:
                    parsed_data.update(data)
        except Exception as e:
            print(f"Warning: Failed to parse JSON block in {filepath}: {e}")
            continue
    return parsed_data

def load_equipments_from_list(data: List[Dict], substat_vars: Dict[str, float] = None) -> Dict[str, EquipmentSet]:
    """Parses a list of full equipment sets."""
    vars = {"$ATK$": 0.0, "$SPD$": 0.0, "$CR$": 0.0, "$CD$": 0.0}
    if substat_vars: vars.update(substat_vars)
    
    registry = {}
    for item in data:
        name = item["name"]
        pieces = {}
        for slot, mod_list in item.get("pieces", {}).items():
            modifiers = []
            if isinstance(mod_list, list):
                for m in mod_list:
                    val = vars.get(m["value"], m["value"]) if isinstance(m["value"], str) else m["value"]
                    modifiers.append(Modifier(StatType[m["stat"]], val, ModifierType[m["type"]]))
            pieces[slot] = EquipmentPiece(name=f"{name}_{slot}", slot=slot, modifiers=modifiers)
            
        set_modifiers = []
        for m in item.get("set_modifiers", item.get("modifiers", [])):
            val = vars.get(m["value"], m["value"]) if isinstance(m["value"], str) else m["value"]
            set_modifiers.append(Modifier(StatType[m["stat"]], val, ModifierType[m["type"]]))
            
        registry[name] = EquipmentSet(name, pieces, set_modifiers, item.get("set_bonus_name", ""))
    return registry

def load_combined_equipments(data: Dict, substat_vars: Dict[str, float] = None) -> Dict[str, EquipmentSet]:
    """Combines 4-piece sets and 2-piece sets into all possible full builds."""
    vars = {"$ATK$": 0.0, "$SPD$": 0.0, "$CR$": 0.0, "$CD$": 0.0}
    if substat_vars: vars.update(substat_vars)

    def parse_mods(mod_list):
        mods = []
        for m in mod_list:
            val = vars.get(m["value"], m["value"]) if isinstance(m["value"], str) else m["value"]
            mods.append(Modifier(StatType[m["stat"]], val, ModifierType[m["type"]]))
        return mods

    base_pieces = {}
    for slot, mods in data.get("base_pieces", {}).items():
        base_pieces[slot] = EquipmentPiece(name=slot, slot=slot, modifiers=parse_mods(mods))

    registry = {}
    for f_name, f_mods_raw in data.get("four_piece_sets", {}).items():
        for t_name, t_mods_raw in data.get("two_piece_sets", {}).items():
            comb_name = f"{f_name}4+{t_name}2"
            combined_set_mods = parse_mods(f_mods_raw) + parse_mods(t_mods_raw)
            registry[comb_name] = EquipmentSet(comb_name, base_pieces, combined_set_mods, f"{f_name}/{t_name}")
    return registry

def load_equipments_from_json(filepath: str, substat_vars: Dict[str, float] = None) -> Dict[str, EquipmentSet]:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict) and "four_piece_sets" in data:
        return load_combined_equipments(data, substat_vars)
    return load_equipments_from_list(data, substat_vars)

def load_equipments_from_df(df) -> Dict[str, EquipmentSet]:
    import pandas as pd
    """
    Expects a DataFrame with columns: name, stat, value, type
    """
    registry = {}
    for name, group in df.groupby("name"):
        modifiers = []
        for _, row in group.iterrows():
            if pd.isna(row["stat"]): continue
            stat_type = StatType[row["stat"]]
            mod_type = ModifierType[row["type"]]
            modifiers.append(Modifier(stat_type, row["value"], mod_type))
        registry[name] = Equipment(name, modifiers)
    return registry

def load_arcanas_from_json(filepath: str) -> Dict[str, Arcana]:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if "arcanas_set" not in data:
        return {}
    
    registry = {}
    for name, a_data in data["arcanas_set"].items():
        modifiers = []
        for m in a_data.get("modifiers", []):
            modifiers.append(Modifier(StatType[m["stat"]], m["val"], ModifierType[m["type"]]))
        registry[name] = Arcana(name, a_data["target"], modifiers, a_data["type"])
    return registry

def load_journeys_from_json(filepath: str) -> Dict[str, Journey]:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if "journeys" not in data:
        return {}
    
    registry = {}
    for name, j_data in data["journeys"].items():
        modifiers = []
        for m in j_data.get("modifiers", []):
            modifiers.append(Modifier(StatType[m["stat"]], m["val"], ModifierType[m["type"]]))
        registry[name] = Journey(name, modifiers, j_data["type"], j_data.get("restrict", {}))
    return registry

def load_blessings_from_json(filepath: str) -> Dict[str, Journey]:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if "arcana_blessing" not in data:
        return {}
    
    registry = {}
    for b_name, b_data in data["arcana_blessing"].items():
        modifiers = []
        if "base_val" in b_data:
            stat = StatType[b_data["stat"]]
            val = b_data["base_val"]
            m_type = ModifierType.PERCENT if b_data["stat"] == "ATK" else ModifierType.FLAT
            modifiers.append(Modifier(stat, val, m_type, f"Blessing_{b_name}"))
        # Treat as journey for system compatibility
        registry[b_name] = Journey(b_name, modifiers, b_name, {})
    return registry
