from Core.models_v3 import StatType
from typing import Dict, List, Callable

def profile_stat_scaling(
    char_name: str, 
    cdata: Dict, 
    rdata: Dict, 
    equip_names: List[str], 
    stat_type: StatType, 
    max_increment: float, 
    step: float, 
    find_best_func: Callable,
    base_vars: Dict = None
) -> List[Dict]:
    """
    특정 스탯(공격력, 치확, 치피)이 0%부터 max_increment까지 step 단위로 증가할 때,
    각 구간별 절대적인 1위 빌드(장비+축복+여정)의 변화를 추적하여 반환합니다.
    """
    var_map = {
        StatType.ATK: "$ATK$", 
        StatType.CRIT_RATE: "$CR$", 
        StatType.CRIT_DAMAGE: "$CD$"
    }
    target_var = var_map.get(stat_type)
    if not target_var:
        return []

    char_class = cdata.get("분류", cdata.get("class", "Unknown"))
    results = []
    
    # 0.0부터 max_increment까지 step 간격으로 반복 (예: 0%, 10%, 20%...)
    current_increment = 0.0
    while current_increment <= max_increment + 1e-9: # 부동소수점 오차 방지
        # Use baseline stats instead of resetting to 0.0
        vars = base_vars.copy() if base_vars else {"$ATK$": 0.0, "$SPD$": 0.0, "$CR$": 0.0, "$CD$": 0.0}
        # Add the increment to the baseline (distributed across 6 pieces as per engine convention)
        vars[target_var] = vars.get(target_var, 0.0) + (current_increment / 6.0) 
        
        best_dps = -1.0
        best_build = {
            "increment": current_increment,
            "equip": "N/A",
            "blessing": "N/A",
            "journeys": "None",
            "dps": 0.0
        }
        
        # 현재 스탯 증가량에서 모든 장비 세트를 순회하며 1위를 찾음
        for eq_name in equip_names:
            # find_best_journeys 함수 호출 (5개 여정, 축복 최적화)
            res = find_best_func(char_name, char_class, cdata, rdata, eq_name, 5, False, vars)
            
            std_jrs, std_bless, std_dps, std_max_h = res["standard"]
            
            if std_dps > best_dps:
                best_dps = std_dps
                best_build = {
                    "increment": current_increment,
                    "equip": eq_name,
                    "blessing": std_bless or "None",
                    "journeys": " | ".join(std_jrs),
                    "dps": best_dps,
                    "max_hit": std_max_h
                }
                
        results.append(best_build)
        current_increment += step
        
    return results