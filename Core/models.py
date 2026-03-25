from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Any

class StatType(Enum):
    ATK = auto()
    SPEED = auto()
    CRIT_RATE = auto()
    CRIT_DAMAGE = auto()
    HP = auto()
    DAMAGE_INCREASE = auto() # DI
    DEF_PEN = auto()
    AG_GAIN = auto() # Action Gauge Gain

class ModifierType(Enum):
    FLAT = auto()
    PERCENT = auto()       # Added to (1 + base)
    MULTIPLICATIVE = auto() # Multiplied to total

@dataclass
class Modifier:
    stat_type: StatType
    value: float
    mod_type: ModifierType = ModifierType.FLAT
    source: str = "Unknown"

@dataclass
class EquipmentPiece:
    name: str = "Unnamed Piece"
    slot: str = "None"
    modifiers: List[Modifier] = field(default_factory=list)

@dataclass
class EquipmentSet:
    name: str
    pieces: Dict[str, EquipmentPiece] = field(default_factory=dict)
    # Fixed set-wide bonuses (e.g., Attack 4-set +20%)
    set_modifiers: List[Modifier] = field(default_factory=list)
    set_bonus_name: str = ""

    def get_all_modifiers(self) -> List[Modifier]:
        all_mods = list(self.set_modifiers) # Start with set-wide bonuses
        for piece in self.pieces.values():
            all_mods.extend(piece.modifiers)
        return all_mods

    def get_modifier_sum(self, stat_type: StatType, mod_type: ModifierType) -> float:
        return sum(mod.value for mod in self.get_all_modifiers() if mod.stat_type == stat_type and mod.mod_type == mod_type)

@dataclass
class Arcana:
    name: str
    target_classes: List[str]
    modifiers: List[Modifier] = field(default_factory=list)
    arcana_type: str = "" # e.g., "assassin", "rangerA"

    def get_modifier_sum(self, stat_type: StatType, mod_type: ModifierType) -> float:
        return sum(mod.value for mod in self.modifiers if mod.stat_type == stat_type and mod.mod_type == mod_type)

@dataclass
class Journey:
    name: str
    modifiers: List[Modifier] = field(default_factory=list)
    journey_type: str = "" # e.g., "AX", "GX"
    restrict: Dict[str, str] = field(default_factory=dict) # e.g., {"char": "키라"} or {"class": "어쌔신"}

    def get_modifier_sum(self, stat_type: StatType, mod_type: ModifierType) -> float:
        return sum(mod.value for mod in self.modifiers if mod.stat_type == stat_type and mod.mod_type == mod_type)

class Character:
    def __init__(self, name: str, char_class: str, base_stats: Dict[StatType, float]):
        self.name = name
        self.char_class = char_class
        self.base_stats = base_stats
        self.permanent_modifiers: List[Modifier] = []
        
    def add_permanent_modifier(self, mod: Modifier):
        self.permanent_modifiers.append(mod)
        
    def get_stat(self, stat_type: StatType, dynamic_modifiers: Optional[List[Modifier]] = None) -> float:
        base = self.base_stats.get(stat_type, 0.0)
        
        flat_sum = 0.0
        percent_sum = 0.0
        multi_factor = 1.0
        
        all_mods = self.permanent_modifiers + (dynamic_modifiers or [])
        
        for mod in all_mods:
            if mod.stat_type == stat_type:
                if mod.mod_type == ModifierType.FLAT:
                    flat_sum += mod.value
                elif mod.mod_type == ModifierType.PERCENT:
                    percent_sum += mod.value
                elif mod.mod_type == ModifierType.MULTIPLICATIVE:
                    multi_factor *= (1.0 + mod.value)
        
        # Standard formula: (Base * (1 + PercentSum) + FlatSum) * MultiFactor
        # Note: In this specific game, ATK% usually applies to Base. 
        # But 'pool' calculation in calc_dps.py is a bit unique. 
        # pool = (Base_Atk + 1250) * (1 + Resonance%) + Resonance_Flat
        # We might need to adjust this per stat.
        
        if stat_type == StatType.ATK or stat_type == StatType.DEF_PEN:
            return (base * (1.0 + percent_sum) + flat_sum) * multi_factor
        
        return (base * (1.0 + percent_sum) + flat_sum) * multi_factor

@dataclass
class Skill:
    name: str
    coeff: float
    di: float = 0.0
    cooldown: int = 1
    is_ult: bool = False
    is_basic: bool = False
    hits: int = 1
    extra_effects: Dict[str, Any] = field(default_factory=dict)
