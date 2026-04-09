#!/usr/bin/env python3
"""
generate_html.py — optimization_guide.md → HTML 변환기
시각화 가이드(Docs/시각화_가이드.md)에 정의된 규격에 따라 동작합니다.
"""
import re
import json
import sys
import os

def parse_optimization_guide(md_path: str) -> list:
    """Parse optimization_guide.md and return a list of character data dicts."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split into character sections by ## heading
    sections = re.split(r'\n## ', content)
    header = sections[0]  # Contains title, nuke specialist, saviors list

    # Extract update date
    update_match = re.search(r'\*\*업데이트 일시\*\*:\s*(.+)', header)
    update_date = update_match.group(1).strip() if update_match else "N/A"

    characters = []
    for sec in sections[1:]:
        char = parse_character_section(sec)
        if char:
            characters.append(char)

    return characters, update_date


def parse_character_section(section: str) -> dict:
    """Parse a single character section."""
    lines = section.strip().split('\n')
    if not lines:
        return None

    raw_name = lines[0].strip()

    # Generate ID and detect badges
    char_id = raw_name
    rawName = raw_name
    name = raw_name
    badges = []

    # Extract base name
    base = re.sub(r'\(.*?\)', '', raw_name).strip()
    name = base

    has_passive = False
    has_target = False

    paren_content = re.findall(r'\(([^)]+)\)', raw_name)
    for p in paren_content:
        # Normalize p
        p_clean = p.replace(' ', '').lower()
        
        if '달속성파티' in p: badges.append('moon')
        if '바니걸' in p: badges.append('bunny')
        if '1lv' in p_clean: 
            badges.append('passive')
            has_passive = True
        if '궁극기미사용' in p: badges.append('noult')
        if '보스1인' in p: 
            badges.append('boss')
            has_target = True
        if '일반3인' in p: 
            badges.append('normal')
            has_target = True
        if '건틀릿4인' in p: 
            badges.append('gauntlet')
            has_target = True

    # Defaults for better clarity
    if not has_passive:
        badges.append('passive4')
    if not has_target:
        # If not specified, it's usually the 'Base' or 'Single' target mode for non-AoE
        # But we'll only label it if it's explicitly 'General' in some cases.
        # For now, let's just ensure Passive is always clear as requested.
        pass

    # Sanitize ID (Include suffixes to prevent card collision)
    safe_id = raw_name.replace('(', '-').replace(')', '').replace(',', '').replace(' ', '-').replace('1lv', '1lv')

    # Parse Standard Strategy table
    std_ranks = []
    std_traj = []
    alt_data = None

    # Find Standard table rows: now 10 columns
    table_pattern = re.compile(
        r'\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*\*\*([0-9,.]+)\*\*\s*\|\s*([0-9,.]+)\s*\|\s*([0-9,.]+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*([0-9,.]+)\s*\|'
    )
    for line in lines:
        m = table_pattern.search(line)
        if m:
            rank = int(m.group(1))
            equip = m.group(2).strip()
            bless = m.group(3).strip()
            journeys_raw = m.group(4).strip()
            dps = float(m.group(5).replace(',', ''))
            max_hit = int(float(m.group(6).replace(',', '')))
            
            # New Stat Columns
            atk = int(float(m.group(7).replace(',', '')))
            cr = m.group(8).strip()
            cd = m.group(9).strip()
            spd = int(float(m.group(10).replace(',', '')))

            # Parse journey names
            journeys = [j.strip() for j in journeys_raw.split('|') if j.strip()]

            std_ranks.append({
                "rank": rank, "equip": equip, "bless": bless, "journeys": journeys, 
                "dps": dps, "maxHit": max_hit, "atk": atk, "cr": cr, "cd": cd, "spd": spd
            })

    # Parse No-Ult peak row: now 10 columns
    alt_pattern = re.compile(
        r'\|\s*\*\*최고점\*\*\s*\|\s*(.+?)\s*\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*\*\*([0-9,.]+)\*\*\s*\|\s*([0-9,.]+)\s*\|\s*([0-9,.]+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*([0-9,.]+)\s*\|'
    )
    for line in lines:
        m = alt_pattern.search(line)
        if m:
            equip = m.group(1).strip()
            bless = m.group(2).strip()
            journeys_raw = m.group(3).strip()
            dps = float(m.group(4).replace(',', ''))
            max_hit = int(float(m.group(5).replace(',', '')))
            atk = int(float(m.group(6).replace(',', '')))
            cr = m.group(7).strip()
            cd = m.group(8).strip()
            spd = int(float(m.group(9).replace(',', '')))
            
            journeys = [j.strip() for j in journeys_raw.split('|') if j.strip()]

            alt_data = {
                "equip": equip, "bless": bless, "journeys": journeys, "dps": dps, "maxHit": max_hit,
                "atk": atk, "cr": cr, "cd": cd, "spd": spd
            }

    # Parse Build Trajectory
    traj_pattern = re.compile(
        r'-\s*\*\*\+\s*([0-9.]+)%\*\*:\s*(.+?)\s*\((\w+)\)\s*\|\s*\*\*DPS:\s*([0-9,.]+)\*\*\s*\|\s*\*\*MaxHit:\s*([0-9,.]+)\*\*\s*\|\s*(.+)'
    )
    current_stat = None
    for line in lines:
        stat_match = re.match(r'-\s*\*\*(.+?)\*\*\s*성장 경로:', line)
        if stat_match:
            current_stat = stat_match.group(1).strip()
            std_traj.append({"stat": current_stat, "rows": []})
            continue

        m = traj_pattern.search(line)
        if m and current_stat and std_traj:
            pct = f"+{m.group(1)}%"
            equip = f"{m.group(2).strip()}({m.group(3)})"
            dps = int(float(m.group(4).replace(',', '')))
            max_hit = int(float(m.group(5).replace(',', '')))
            js_raw = m.group(6).strip()
            js = [j.strip() for j in js_raw.split('|') if j.strip()]

            std_traj[-1]["rows"].append({
                "pct": pct,
                "equip": equip,
                "dps": dps,
                "maxHit": max_hit,
                "js": js
            })

    peak_dps = std_ranks[0]["dps"] if std_ranks else 0
    peak_max_hit = max([r["maxHit"] for r in std_ranks], default=0) if std_ranks else 0

    return {
        "id": safe_id,
        "rawName": rawName,
        "name": name,
        "badges": badges,
        "peakDPS": peak_dps,
        "maxHit": peak_max_hit,
        "std": {
            "ranks": std_ranks,
            "traj": std_traj
        },
        "alt": alt_data or {"equip": "N/A", "bless": "N/A", "journeys": [], "dps": 0, "maxHit": 0, "atk": 0, "cr": "0%", "cd": "0%", "spd": 0}
    }


# I18n Mappings
TRANSLATIONS = {
    "ko": {
        "title": "스타 세이비어 — 최적화 가이드",
        "header_sub": "구원자 최적화 가이드",
        "update": "업데이트",
        "search_ph": "캐릭터 이름으로 검색...",
        "sim_title": "실시간 커스텀 시뮬레이터",
        "sim_ax_badge": "AX 축복 고정",
        "sim_char": "캐릭터",
        "sim_spec": "패시브/특수환경",
        "sim_passive_lv": "패시브 레벨",
        "sim_lv4": "최대 (4lv)",
        "sim_lv1": "초기 (1lv)",
        "sim_target": "타겟 환경",
        "sim_normal": "일반 모드 (3인)",
        "sim_boss": "보스 모드 (1인)",
        "sim_gauntlet": "건틀릿 레이드 (4인)",
        "sim_duration": "시뮬레이션 기간",
        "sim_long": "장기전 (15턴)",
        "sim_mid": "중기전 (10턴)",
        "sim_short": "단기전 (5턴)",
        "sim_burst": "건틀릿 버스트 (3턴)",
        "sim_atk": "공격력 (%)",
        "sim_cr": "치확 (%)",
        "sim_cd": "치피 (%)",
        "sim_spd": "속도",
        "sim_loading": "엔진 로딩 중...",
        "sim_run": "시뮬레이션 실행",
        "sidebar_title": "구원자 목록",
        "label_peak_dps": "최고 DPS",
        "label_peak_total": "최고 Total Dmg (3T)",
        "tab_std": "🔹 일반 전략 (궁극기 사용)",
        "tab_alt": "🔸 노울트 전략 (AX 특화)",
        "th_rank": "순위",
        "th_gear": "장비 세트",
        "th_bless": "축복",
        "th_journey": "최적 여정 조합 (Top 5)",
        "th_dps": "DPS",
        "th_maxhit": "MaxHit",
        "traj_title": "빌드 진화 경로",
        "alt_desc": "궁극기를 포기하고 AX 스택 피해량에 올인한 특수 상황용 고점 빌드입니다.",
        "peak_build": "최고점",
        "badges": {
            "moon": {"cls":"badge-moon", "label":"달속성 파티"},
            "bunny": {"cls":"badge-bunny", "label":"바니걸"},
            "passive": {"cls":"badge-passive", "label":"패시브 1lv"},
            "passive4": {"cls":"badge-passive4", "label":"패시브 4lv (최대)"},
            "noult": {"cls":"badge-noult", "label":"궁극기 미사용"},
            "boss": {"cls":"badge-boss", "label":"보스 1인"},
            "normal": {"cls":"badge-normal", "label":"일반 3인"},
            "gauntlet": {"cls":"badge-gauntlet", "label":"건틀릿 4인"}
        },
        "lang_name": "EN English",
        "lang_link": "index_en.html"
    },
    "en": {
        "title": "Star Savior — Optimization Guide",
        "header_sub": "Savior Optimization Guide",
        "update": "Updated",
        "search_ph": "Search by savior name...",
        "sim_title": "Real-time Custom Simulator",
        "sim_ax_badge": "AX Blessing Fixed",
        "sim_char": "Savior",
        "sim_spec": "Passive / Special",
        "sim_passive_lv": "Passive Level",
        "sim_lv4": "Max (Lv.4)",
        "sim_lv1": "Base (Lv.1)",
        "sim_target": "Target Environment",
        "sim_normal": "Normal Mode (3 Units)",
        "sim_boss": "Boss Mode (1 Unit)",
        "sim_gauntlet": "Gauntlet Raid (4 Units)",
        "sim_duration": "Simulation Duration",
        "sim_long": "Long Battle (15 Turns)",
        "sim_mid": "Mid Battle (10 Turns)",
        "sim_short": "Short Battle (5 Turns)",
        "sim_burst": "Gauntlet Burst (3 Turns)",
        "sim_atk": "ATK (%)",
        "sim_cr": "Crit Rate (%)",
        "sim_cd": "Crit Dmg (%)",
        "sim_spd": "Speed",
        "sim_loading": "Loading Engine...",
        "sim_run": "Run Simulation",
        "sidebar_title": "Savior List",
        "label_peak_dps": "Peak DPS",
        "label_peak_total": "Peak Total Dmg (3T)",
        "tab_std": "🔹 Standard (With Ult)",
        "tab_alt": "🔸 AX Specialized (No Ult)",
        "th_rank": "Rank",
        "th_gear": "Gear Set",
        "th_bless": "Bless",
        "th_journey": "Best Journey Setup (Top 5)",
        "th_dps": "DPS",
        "th_maxhit": "MaxHit",
        "traj_title": "Build Evolution Path",
        "alt_desc": "A high-peak build specialized in AX stack damage instead of Ultimate.",
        "peak_build": "Peak Build",
        "badges": {
            "moon": {"cls":"badge-moon", "label":"Moon Team"},
            "bunny": {"cls":"badge-bunny", "label":"Bunny Girl"},
            "passive": {"cls":"badge-passive", "label":"Passive Lv.1"},
            "passive4": {"cls":"badge-passive4", "label":"Passive Lv.4 (Max)"},
            "noult": {"cls":"badge-noult", "label":"No Ult"},
            "boss": {"cls":"badge-boss", "label":"Boss (S)"},
            "normal": {"cls":"badge-normal", "label":"General (T)"},
            "gauntlet": {"cls":"badge-gauntlet", "label":"Gauntlet (Q)"}
        },
        "lang_name": "KO 한국어",
        "lang_link": "index.html"
    }
}

# Data Content Translations
DATA_TRANSLATIONS = {
    "en": {
        "characters": {
            "프레이": "Frey",
            "로자리아": "Rosaria",
            "유미나": "Yumina",
            "힐데": "Hilde",
            "루나": "Luna",
            "리디아": "Lydia",
            "릴리": "Lily",
            "샤를": "Charles",
            "에핀델": "Epindel",
            "클레어": "Claire",
            "스마일": "Smile",
            "스칼렛": "Scarlet",
            "키라": "Kira",
            "레이시": "Lacey",
            "뮤리엘": "Muriel",
            "아세라": "Asera"
        },
        "equipments": {
            "파괴": "Destruction",
            "공격": "Attack",
            "투지": "Valor",
            "보조": "Support",
            "장벽": "Barrier",
            "통찰": "Insight",
            "체력": "HP",
            "속도": "Speed"
        },
        "journeys": {
            "노페인 노게인": "No Pain No Gain",
            "누각 위, 유리달 맞이": "Crystal Moon on Pavilion",
            "하늘의 심판": "Judgment from Above",
            "메이드 바이 페트라": "Made by Petra",
            "어느 한 기사의 맹세": "Oath of a Knight",
            "불굴의 역작": "Indomitable Masterpiece",
            "깊은 애도": "Deep Mourning",
            "친구들과의 산책": "Stroll with Friends",
            "키라만큼 귀여워": "Cute as Kira",
            "허수의 개척자": "Pioneer of Imaginary",
            "완벽한 바니걸": "Perfect Bunny Girl",
            "경력직 용병": "Veteran Mercenary",
            "피의 메아리": "Blood Echo"
        },
        "misc": {
            "달속성파티": "Moon Team",
            "바니걸": "Bunny Girl",
            "궁극기미사용": "No Ult",
            "궁극기 미사용 (AX특화)": "No Ult (AX Spec)",
            "패시브1lv": "Passive Lv.1",
            "보스1인": "Boss (Single)",
            "일반3인": "General (3-Target)",
            "건틀릿4인": "Gauntlet (4-Target)",
            "빌드 진화 경로": "Build Path",
            "공격력%": "ATK%",
            "치명타 피해": "Crit Dmg",
            "치명타 확률": "Crit Rate"
        }
    }
}


def translate_text(text: str, lang: str) -> str:
    if lang != "en":
        return text
    
    mapping = DATA_TRANSLATIONS["en"]
    
    # 1. Handle exact matches in journeys (complex names)
    if text in mapping["journeys"]:
        return mapping["journeys"][text]
    
    # 2. Handle Equipment sets (e.g., "파괴4+투지2")
    # Replace set names
    processed = text
    for ko, en in mapping["equipments"].items():
        processed = processed.replace(ko, en)
        
    # 3. Handle specific character names and their suffixes
    # Example: "프레이(달속성파티, 1lv)"
    for ko, en in mapping["characters"].items():
        if ko in processed:
            processed = processed.replace(ko, en)
            
    # 4. Handle Misc terms (badges/suffixes inside parentheses)
    for ko, en in mapping["misc"].items():
        # Handle cases like "달속성파티" or "1lv" -> "Lv.1"
        processed = processed.replace(ko, en)
        
    # Cleanup formatting if needed
    processed = processed.replace(", 1lv", ", Lv.1").replace("1lv", "Lv.1")
    
    return processed

def translate_data_recursive(obj, lang: str):
    if lang != "en":
        return obj
    
    if isinstance(obj, list):
        return [translate_data_recursive(item, lang) for item in obj]
    
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            # 기술적인 키(Key)는 그대로 유지하고, 표시용 값(Value)만 선별적으로 번역
            if k in ["name", "equip", "bless", "stat"]:
                new_dict[k] = translate_text(v, lang)
            elif k in ["badges", "journeys", "js"]:
                if isinstance(v, list):
                    new_dict[k] = [translate_text(x, lang) for x in v if isinstance(x, str)]
                else:
                    new_dict[k] = v
            elif k == "rawName":
                # 시뮬레이션 엔진이 참조하는 원본 이름은 절대로 번역하지 않음
                new_dict[k] = v 
            else:
                # 그 외 구조적 데이터(id, dps, maxHit 등)는 그대로 재귀 탐색
                new_dict[k] = translate_data_recursive(v, lang)
        return new_dict
    
    if isinstance(obj, str):
        # 최상위 레벨 문자열이 전달될 경우 처리 (보통 list/dict 내부에서 처리됨)
        return translate_text(obj, lang)
        
    return obj


HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>스타 세이비어 — 최적화 가이드</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<!-- PyScript Integration -->
<link rel="stylesheet" href="https://pyscript.net/releases/2023.11.1/core.css" />
<script type="module" src="https://pyscript.net/releases/2023.11.1/core.js"></script>
<py-config>
  packages = ["pandas"]
</py-config>
<script id="vfs-bundled" type="application/json">%%VFS_DATA%%</script>
<style>
  :root {
    --bg: #051C2C;           /* McKinsey Deep Blue */
    --bg2: #0E2B3E;          /* Card Background */
    --bg3: #16364D;          /* Section Background */
    --bg4: #1E4660;          /* Hover Background */
    --border: #244C6A;       /* Subtle Border */
    --border2: #2E5C7D;      /* Stronger Border */
    --gold: #E6B01E;         /* Corporate Gold (Accent) */
    --gold2: #C59618;
    --blue: #007DBB;         /* Professional Blue */
    --blue2: #005A87;
    --red: #C52A1A;          /* Corporate Red */
    --green: #168B16;        /* Stable Green */
    --purple: #6A5ACD;
    --orange: #E66E19;
    --text: #FFFFFF;         /* Primary White */
    --text2: #9199A3;        /* Professional Gray */
    --text3: #637285;
    --rank1: #E6B01E;
    --rank2: #9199A3;
    --rank3: #CD7F32;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
    line-height: 1.5;
  }

  header {
    position: sticky; top: 0; z-index: 100;
    background: rgba(5, 28, 44, 0.95);
    backdrop-filter: blur(12px);
    border-bottom: 2px solid var(--blue);
    padding: 0 24px;
    display: flex; align-items: center; gap: 16px; height: 64px;
  }
  .logo { font-size: 14px; font-weight: 800; letter-spacing: 0.1em; color: #fff; text-transform: uppercase; white-space: nowrap; }
  .logo::before { content: '■'; color: var(--blue); margin-right: 8px; }
  .header-sep { flex: 1; }
  .lang-btn {
    text-decoration: none; font-size: 11px; font-weight: 700; color: var(--text2);
    padding: 6px 12px; border: 1px solid var(--border); border-radius: 4px;
    transition: all 0.2s; margin-right: 16px;
  }
  .lang-btn:hover { border-color: var(--blue); color: var(--text); background: rgba(0, 125, 187, 0.1); }
  .update-badge { font-size: 11px; color: var(--text2); font-family: 'JetBrains Mono', monospace; opacity: 0.8; }

  .search-wrap { padding: 24px 24px 0; max-width: 1400px; margin: 0 auto; }
  .search-box { position: relative; width: 100%; max-width: 480px; }
  .search-box input {
    width: 100%; hide-focus: outline;
    background: var(--bg2); border: 1px solid var(--border);
    color: var(--text); padding: 12px 16px 12px 40px; border-radius: 4px;
    font-size: 14px; font-family: 'Inter', sans-serif; outline: none;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .search-box input:focus { border-color: var(--blue); box-shadow: 0 0 0 4px rgba(0, 125, 187, 0.2); }
  .search-box input::placeholder { color: var(--text3); }
  .search-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: var(--text3); font-size: 16px; pointer-events: none; }

  .layout { display: flex; max-width: 1400px; margin: 0 auto; padding: 24px 24px 80px; gap: 32px; align-items: flex-start; }

  .sidebar {
    width: 240px; flex-shrink: 0; position: sticky; top: 88px;
    max-height: calc(100vh - 120px); overflow-y: auto;
    padding-right: 8px;
  }
  .sidebar::-webkit-scrollbar { width: 4px; }
  .sidebar::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
  .sidebar-title { font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase; color: var(--text2); font-weight: 800; padding-bottom: 12px; border-bottom: 2px solid var(--border); margin-bottom: 12px; }
  .nav-item { 
    display: block; padding: 10px 12px; border-radius: 4px; font-size: 13px; color: var(--text2); cursor: pointer; transition: all 0.2s; 
    line-height: 1.4; border: none; background: none; text-align: left; width: 100%;
    border-left: 3px solid transparent; margin-bottom: 4px;
  }
  .nav-item:hover { background: var(--bg4); color: var(--text); }
  .nav-item.active { background: rgba(0, 125, 187, 0.1); color: var(--blue); border-left-color: var(--blue); font-weight: 600; }

  .main { flex: 1; min-width: 0; }

  .char-card { background: var(--bg2); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 24px; overflow: hidden; transition: box-shadow 0.3s ease; }
  .char-card:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
  .char-card.hidden { display: none; }
  .char-header { display: flex; align-items: center; padding: 20px 24px; cursor: pointer; gap: 16px; user-select: none; background: var(--bg3); border-bottom: 1px solid var(--border); }
  .char-header:hover { background: var(--bg4); }
  .char-name { font-size: 18px; font-weight: 800; flex: 1; letter-spacing: -0.02em; }
  .char-badge { font-size: 10px; padding: 4px 10px; border-radius: 2px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
  .badge-moon { background: rgba(106, 90, 205, 0.15); color: #9B9AFF; border: 1px solid rgba(106, 90, 205, 0.3); }
  .badge-bunny { background: rgba(230, 110, 25, 0.12); color: var(--orange); border: 1px solid rgba(230, 110, 25, 0.25); }
  .badge-passive { background: rgba(145, 153, 163, 0.1); color: var(--text2); border: 1px solid var(--border2); }
  .badge-passive4 { background: rgba(22, 139, 22, 0.15); color: #4CAF50; border: 1px solid rgba(22, 139, 22, 0.3); }
  .badge-noult { background: rgba(197, 42, 26, 0.1); color: #FF6B6B; border: 1px solid rgba(197, 42, 26, 0.25); }
  .badge-boss { background: rgba(230, 176, 30, 0.1); color: var(--gold); border: 1px solid rgba(230, 176, 30, 0.3); }
  .badge-normal { background: rgba(0, 125, 187, 0.15); color: var(--blue-light); border: 1px solid rgba(0, 125, 187, 0.3); }
  .badge-gauntlet { background: rgba(197, 42, 26, 0.15); color: #FF4D4D; border: 1px solid rgba(197, 42, 26, 0.3); }

  .dps-peak { font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 800; color: var(--gold); }
  .dps-label { font-size: 10px; color: var(--text2); text-transform: uppercase; letter-spacing: 0.08em; margin-right: 6px; }
  .chevron { font-size: 12px; color: var(--text3); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
  .char-card.open .chevron { transform: rotate(180deg); color: var(--blue); }
  .char-body { display: none; padding: 24px; background: var(--bg2); }
  .char-card.open .char-body { display: block; }

  .strat-tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 4px; }
  .strat-tab { padding: 8px 16px; font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s; border: none; background: none; color: var(--text3); position: relative; }
  .strat-tab::after { content: ''; position: absolute; bottom: -5px; left: 0; width: 100%; height: 3px; background: transparent; transition: all 0.2s; }
  .strat-tab.active-std { color: var(--blue); }
  .strat-tab.active-std::after { background: var(--blue); }
  .strat-tab.active-alt { color: var(--orange); }
  .strat-tab.active-alt::after { background: var(--orange); }
  .strat-tab:hover { color: var(--text); }

  .strat-panel { display: none; animation: fadeIn 0.3s ease-out; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
  .strat-panel.visible { display: block; }

  .rank-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 24px; }
  .rank-table th { padding: 12px 10px; text-align: left; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text2); font-weight: 800; border-bottom: 2px solid var(--border); }
  .rank-table td { padding: 14px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  .rank-table tr:hover td { background: rgba(255,255,255,0.03); }

  .rank-num { font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 800; width: 40px; }
  .rank-1 { color: var(--rank1); }
  .rank-2 { color: var(--rank2); }
  .rank-3 { color: var(--rank3); }

  .equip-tag { display: inline-block; font-size: 11px; padding: 3px 8px; border-radius: 2px; background: var(--bg3); color: var(--text); border: 1px solid var(--border); font-family: 'JetBrains Mono', monospace; }
  .bless-tag { display: inline-block; font-size: 11px; padding: 2px 7px; border-radius: 2px; background: rgba(230, 176, 30, 0.08); color: var(--gold); font-weight: 800; border: 1px solid rgba(230, 176, 30, 0.2); }

  .journey-list { display: flex; flex-wrap: wrap; gap: 6px; }
  .j-tag { font-size: 11px; padding: 2px 8px; border-radius: 3px; background: rgba(0, 125, 187, 0.08); color: var(--blue-light); border: 1px solid rgba(0, 125, 187, 0.2); }

  .dps-val { font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 800; color: #4CAF50; }
  .maxhit-val { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: var(--gold); }

  .traj-section { margin-top: 12px; }
  .traj-title { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text3); margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
  .traj-title::after { content: ''; flex: 1; height: 1px; background: var(--border); }
  .traj-stat { margin-bottom: 12px; }
  .traj-stat-name { font-size: 11px; font-weight: 600; color: var(--text2); margin-bottom: 6px; display: flex; align-items: center; gap: 4px; }
  .traj-stat-name::before { content: ''; width: 3px; height: 12px; border-radius: 2px; background: var(--blue); display: inline-block; }
  .traj-row { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 6px; background: var(--bg); margin-bottom: 3px; font-size: 12px; flex-wrap: wrap; }
  .pct-pill { font-family: 'JetBrains Mono', monospace; font-size: 10px; padding: 1px 6px; border-radius: 3px; background: var(--bg4); color: var(--text3); min-width: 48px; text-align: center; }
  .traj-equip { color: var(--text2); font-size: 11px; }
  .traj-dps { font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; color: var(--green); min-width: 50px; }
  .traj-maxhit { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; color: var(--gold); min-width: 60px; }
  .traj-journeys { display: flex; flex-wrap: wrap; gap: 3px; flex: 1; }
  .tj { font-size: 10px; padding: 1px 5px; border-radius: 3px; background: rgba(74,158,255,0.07); color: var(--blue); border: 1px solid rgba(74,158,255,0.15); }

  .peak-box { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: rgba(255,87,87,0.05); border: 1px solid rgba(255,87,87,0.15); border-radius: 8px; margin-top: 8px; flex-wrap: wrap; }
  .peak-label { font-size: 11px; color: var(--red); font-weight: 700; min-width: 44px; }
  .peak-equip { font-size: 12px; color: var(--text2); }
  .peak-dps { font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 700; color: var(--gold); margin-left: auto; }
  .peak-maxhit { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: var(--red); }

  .empty-state { text-align: center; padding: 60px 20px; color: var(--text3); font-size: 14px; }

  @media (max-width: 768px) {
    .sidebar { display: none; }
    .layout { padding: 12px 12px 40px; }
  .rank-table { font-size: 11px; }
  }

  /* Custom Simulator UI Styles */
  .custom-sim-wrap {
    background: var(--bg2); border: 1px solid var(--border); border-radius: 12px;
    padding: 24px; margin-bottom: 24px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  }
  .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 16px; }
  .form-group { display: flex; flex-direction: column; gap: 6px; }
  .form-group label { font-size: 11px; font-weight: 700; color: var(--text2); text-transform: uppercase; letter-spacing: 0.1em; }
  .form-group input, .form-group select {
    background: var(--bg3); border: 1px solid var(--border2); color: var(--text);
    padding: 10px 14px; border-radius: 6px; font-family: 'JetBrains Mono', monospace;
    font-size: 14px; outline: none; transition: border-color 0.2s;
  }
  .form-group input:focus, .form-group select:focus { border-color: var(--blue); }
  .sim-btn {
    background: var(--blue2); color: #fff; border: none; padding: 12px 24px;
    border-radius: 6px; font-size: 14px; font-weight: 700; cursor: pointer;
    transition: background 0.2s; width: 100%; letter-spacing: 0.05em;
    margin-top: 8px;
  }
  .sim-btn:hover { background: #3b8ce0; }
  .sim-btn:disabled { background: var(--border2); cursor: not-allowed; }
  @keyframes spin { to { transform: rotate(360deg); } }

  footer {
    padding: 60px 24px 100px;
    text-align: center;
    border-top: 1px solid var(--border);
    margin-top: 80px;
  }
  .footer-link {
    color: var(--text3);
    text-decoration: none;
    font-size: 13px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: color 0.2s;
  }
  .footer-link:hover {
    color: var(--blue);
  }
  .footer-logo {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 11px;
    margin-top: 16px;
    color: var(--text3);
    opacity: 0.6;
    letter-spacing: 0.05em;
  }
</style>
</head>
<body>

<header>
  <div class="logo">⭐ Star Savior</div>
  <span style="color:var(--text3);font-size:13px;">{{HEADER_SUB}}</span>
  <div class="header-sep"></div>
  <a href="{{LANG_LINK}}" class="lang-btn">{{LANG_NAME}}</a>
  <div class="update-badge">{{UPDATE}}: %%UPDATE_DATE%%</div>
</header>

<div class="search-wrap">
  <div class="search-box">
    <span class="search-icon">🔍</span>
    <input type="text" id="searchInput" placeholder="{{SEARCH_PH}}" oninput="filterChars()">
  </div>
</div>

<div class="layout">
  <nav class="sidebar" id="sidebar"></nav>
  <main class="main" id="main">
    <div class="custom-sim-wrap">
      <h2 style="font-size:16px; margin-bottom:16px; display:flex; align-items:center; gap:8px;">
        ⚙️ {{SIM_TITLE}} <span class="badge-boss" style="padding: 2px 6px; border-radius: 4px; font-size: 10px;">{{SIM_AX_BADGE}}</span>
      </h2>
      <div class="form-grid">
        <div class="form-group">
          <label>{{SIM_CHAR}}</label>
          <select id="simCharBase" onchange="updateSimDropdowns('base')">
            <option value="">불러오는 중...</option>
          </select>
        </div>
        <div class="form-group">
          <label>{{SIM_SPEC}}</label>
          <select id="simSpec" onchange="updateSimDropdowns('spec')">
            <option value="-">-</option>
          </select>
        </div>
        <div class="form-group" id="simPassiveWrap" style="display:none;">
           <label>{{SIM_PASSIVE_LV}}</label>
           <select id="simPassive">
             <option value="base">{{SIM_LV4}}</option>
             <option value="1lv">{{SIM_LV1}}</option>
           </select>
        </div>
        <div class="form-group">
          <label>{{SIM_TARGET}}</label>
          <select id="simTarget">
            <option value="3">{{SIM_NORMAL}}</option>
            <option value="1">{{SIM_BOSS}}</option>
            <option value="4">{{SIM_GAUNTLET}}</option>
          </select>
        </div>
        <div class="form-group">
          <label>{{SIM_DURATION}}</label>
          <select id="simTurns">
            <option value="15">{{SIM_LONG}}</option>
            <option value="10">{{SIM_MID}}</option>
            <option value="5">{{SIM_SHORT}}</option>
            <option value="3">{{SIM_BURST}}</option>
          </select>
        </div>
      </div>
      <div class="form-grid" style="grid-template-columns: repeat(4, 1fr); margin-top: 20px; border-top: 1px solid var(--border); padding-top: 16px;">
        <div class="form-group">
          <label>{{SIM_ATK}}</label>
          <input type="number" id="simAtk" value="0.0" step="0.1">
        </div>
        <div class="form-group">
          <label>{{SIM_CR}}</label>
          <input type="number" id="simCr" value="0.0" step="0.1">
        </div>
        <div class="form-group">
          <label>{{SIM_CD}}</label>
          <input type="number" id="simCd" value="0.0" step="0.1">
        </div>
        <div class="form-group">
          <label>{{SIM_SPD}}</label>
          <input type="number" id="simSpd" value="0.0" step="0.1">
        </div>
      </div>
      <button class="sim-btn" id="simBtn" py-click="run_simulation" disabled>
        <span class="btn-text">{{SIM_LOADING}}</span>
        <div class="loader" id="simLoader"></div>
      </button>
      <div id="simStatus" style="margin-top: 10px; font-size: 11px; color: var(--text3); font-family: 'JetBrains Mono', monospace; display: none; padding: 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 4px;"></div>
      <div id="simResult" style="margin-top: 20px; display: none;"></div>
    </div>
    
    <!-- Existing Char Cards Container -->
    <div id="charContainer"></div>
  </main>
</div>

<footer>
  <a href="https://github.com/mingijuk-lab/star-savior-sim" target="_blank" class="footer-link">
    <svg height="20" width="20" viewBox="0 0 16 16" fill="currentColor" style="display:inline-block; vertical-align:middle;"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg>
    <span>GitHub Repository</span>
  </a>
  <div class="footer-logo">© 2024-2026 mingijuk-lab. Star Savior Simulation Engine v5.0</div>
</footer>

<script>
const data = %%DATA_JSON%%;
const LANG = "{{LANG}}";

const badgeMap = %%BADGE_MAP%%;

function renderBadges(badges) {
  return badges.map(b => `<span class="char-badge ${badgeMap[b].cls}">${badgeMap[b].label}</span>`).join('');
}
function journeyTags(js) {
  return js.map(j => `<span class="j-tag">${j}</span>`).join('');
}
function trajJourneyTags(js) {
  return js.map(j => `<span class="tj">${j}</span>`).join('');
}
function fmt(n) { 
  if (n === undefined || n === null || isNaN(n)) return "0.00";
  return n.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2}); 
}
function fmtInt(n) { 
  if (n === undefined || n === null || isNaN(n)) return "0";
  return n.toLocaleString(); 
}

function buildCard(char) {
  const stdId = `std-${char.id}`;
  const altId = `alt-${char.id}`;

  const rankRows = char.std.ranks.map(r => `
    <tr>
      <td><span class="rank-num rank-${r.rank}">${r.rank}</span></td>
      <td><span class="equip-tag">${r.equip}</span></td>
      <td><span class="bless-tag">${r.bless}</span></td>
      <td><div class="journey-list">${journeyTags(r.journeys)}</div></td>
      <td><span class="dps-val">${fmt(r.dps)}</span></td>
      <td><span class="maxhit-val">${fmtInt(r.maxHit)}</span></td>
    </tr>
  `).join('');

  const trajSections = char.std.traj.map(ts => `
    <div class="traj-stat">
      <div class="traj-stat-name">${ts.stat}</div>
      ${ts.rows.map(row => `
        <div class="traj-row">
          <span class="pct-pill">${row.pct}</span>
          <span class="traj-equip">${row.equip}</span>
          <span class="traj-dps">${fmtInt(row.dps)}</span>
          <span class="traj-maxhit">💥${fmtInt(row.maxHit)}</span>
          <div class="traj-journeys">${trajJourneyTags(row.js)}</div>
        </div>
      `).join('')}
    </div>
  `).join('');

  return `
  <div class="char-card" id="card-${char.id}">
    <div class="char-header" onclick="toggleCard('${char.id}')">
      <span class="char-name">${char.name}</span>
      ${renderBadges(char.badges)}
      <div style="margin-left:auto;display:flex;align-items:center;gap:12px;">
        <span class="dps-label">${char.badges.includes('gauntlet') ? '{{LABEL_PEAK_TOTAL}}' : '{{LABEL_PEAK_DPS}}'}</span><span class="dps-peak">${fmt(char.peakDPS)}</span>
        <span class="chevron">▼</span>
      </div>
    </div>
    <div class="char-body">
      <div class="strat-tabs">
        <button class="strat-tab active-std" id="tab-std-${char.id}" onclick="switchTab('${char.id}','std')">{{TAB_STD}}</button>
        <button class="strat-tab" id="tab-alt-${char.id}" onclick="switchTab('${char.id}','alt')">{{TAB_ALT}}</button>
      </div>

      <div class="strat-panel visible" id="${stdId}">
        <table class="rank-table">
          <thead>
            <tr>
              <th>{{TH_RANK}}</th><th>{{TH_GEAR}}</th><th>{{TH_BLESS}}</th><th>{{TH_JOURNEY}}</th><th>{{TH_DPS}}</th><th>{{TH_MAXHIT}}</th><th>ATK</th><th>CR</th><th>CD</th><th>SPD</th>
            </tr>
          </thead>
          <tbody>
            ${char.std.ranks.map(r => `
              <tr>
                <td class="rank-num rank-${r.rank}">${r.rank}</td>
                <td><span class="equip-tag">${r.equip}</span></td>
                <td><span class="bless-tag">${r.bless}</span></td>
                <td><div class="journey-list">${r.journeys.map(j => `<span class="j-tag">${j}</span>`).join('')}</div></td>
                <td><span class="dps-val">${fmt(r.dps)}</span></td>
                <td><span class="maxhit-val">${fmtInt(r.maxHit)}</span></td>
                <td style="color:var(--text2);font-size:11px;">${fmtInt(r.atk)}</td>
                <td style="color:var(--text2);font-size:11px;">${r.cr}</td>
                <td style="color:var(--text2);font-size:11px;">${r.cd}</td>
                <td style="color:var(--text2);font-size:11px;">${r.spd}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        <div class="traj-section">
          <div class="traj-title">{{TRAJ_TITLE}}</div>
          ${trajSections}
        </div>
      </div>

      <div class="strat-panel" id="${altId}">
        <div style="font-size:12px;color:var(--text3);margin-bottom:12px;">{{ALT_DESC}}</div>
        <div class="peak-box">
          <div style="display:flex; flex-direction:column; gap:4px; flex:1;">
            <div style="display:flex; align-items:center; gap:8px;">
               <span class="peak-label">{{PEAK_BUILD}}</span>
               <span class="peak-equip"><span class="equip-tag">${char.alt.equip}</span>&nbsp;<span class="bless-tag">${char.alt.bless}</span></span>
               <span class="peak-dps" style="margin-left:auto;">${fmt(char.alt.dps)}</span>
            </div>
            <div class="journey-list">${char.alt.journeys.map(j => `<span class="j-tag">${j}</span>`).join('')}</div>
            <div style="font-size:11px; color:var(--text3); border-top:1px solid var(--border); padding-top:4px; display:flex; gap:12px;">
               <span>ATK: ${fmtInt(char.alt.atk)}</span> | <span>CR: ${char.alt.cr}</span> | <span>CD: ${char.alt.cd}</span> | <span>SPD: ${char.alt.spd}</span>
               <span style="margin-left:auto; color:var(--gold);">💥${fmtInt(char.alt.maxHit)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>`;
}

function buildSidebar() {
  const sidebar = document.getElementById('sidebar');
  let html = `<div class="sidebar-title">{{SIDEBAR_TITLE}}</div>`;
  data.forEach(c => {
    const badgeText = c.badges.map(b => badgeMap[b].label).join(' · ');
    html += `<button class="nav-item" id="nav-${c.id}" onclick="scrollToCard('${c.id}')">${c.name}${badgeText ? `<br><span style="font-size:10px;color:var(--text3);">${badgeText}</span>` : ''}</button>`;
  });
  sidebar.innerHTML = html;
}

function toggleCard(id) {
  document.getElementById(`card-${id}`).classList.toggle('open');
}

function switchTab(id, which) {
  const stdPanel = document.getElementById(`std-${id}`);
  const altPanel = document.getElementById(`alt-${id}`);
  const stdTab = document.getElementById(`tab-std-${id}`);
  const altTab = document.getElementById(`tab-alt-${id}`);
  if (which === 'std') {
    stdPanel.classList.add('visible'); altPanel.classList.remove('visible');
    stdTab.className = 'strat-tab active-std'; altTab.className = 'strat-tab';
  } else {
    altPanel.classList.add('visible'); stdPanel.classList.remove('visible');
    altTab.className = 'strat-tab active-alt'; stdTab.className = 'strat-tab';
  }
}

function scrollToCard(id) {
  const card = document.getElementById(`card-${id}`);
  if (!card.classList.contains('open')) card.classList.add('open');
  card.scrollIntoView({ behavior: 'smooth', block: 'start' });
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`nav-${id}`).classList.add('active');
}

function filterChars() {
  const q = document.getElementById('searchInput').value.trim().toLowerCase();
  data.forEach(c => {
    const card = document.getElementById(`card-${c.id}`);
    const nav = document.getElementById(`nav-${c.id}`);
    const badgeText = c.badges.map(b => badgeMap[b].label).join(' ');
    const match = !q || c.name.toLowerCase().includes(q) || badgeText.toLowerCase().includes(q) || c.id.toLowerCase().includes(q);
    card.classList.toggle('hidden', !match);
    nav.style.display = match ? '' : 'none';
  });
  const empty = document.getElementById('empty');
  if (empty) {
    const visible = data.filter(c => !document.getElementById(`card-${c.id}`).classList.contains('hidden'));
    empty.style.display = visible.length === 0 ? 'block' : 'none';
  }
}

// Simulation UI Grouping Logic
window.charVariants = {};

function buildCharTree() {
  data.forEach(c => {
    const raw = c.rawName; // Use Original Raw Name for Simulation lookup
    const id = c.id;       // Use Sanitized ID for HTML elements
    const base = c.name;   // Clean base name
    
    if (!charVariants[base]) {
      charVariants[base] = {
        name: base,
        specs: {},
        passives: new Set(),
        targets: new Set()
      };
    }
    
    // Parse spec and level from raw if possible
    const isEn = (LANG === 'en');
    let spec = isEn ? 'Standard' : 'Standard'; // Just a placeholder, we use mapping below
    
    if (raw.includes('달속성파티')) spec = isEn ? 'Moon Team' : '달속성 파티';
    else if (raw.includes('바니걸')) spec = isEn ? 'Bunny Girl' : '바니걸';
    else if (raw.includes('궁극기미사용')) spec = isEn ? 'No Ult (AX Spec)' : '궁극기 미사용 (AX특화)';
    else spec = isEn ? 'Standard' : '일반';
    
    let lv = '4lv';
    if (raw.includes('1lv')) lv = '1lv';
    
    let target = 'both';
    if (raw.includes('보스1인')) target = '1';
    if (raw.includes('일반3인')) target = '3';

    if (!charVariants[base].specs[spec]) charVariants[base].specs[spec] = [];
    charVariants[base].specs[spec].push({ raw, lv, target });
    charVariants[base].passives.add(lv);
    if (target !== 'both') charVariants[base].targets.add(target);
  });
}

function updateSimDropdowns(trigger) {
  const baseSelect = document.getElementById('simCharBase');
  const specSelect = document.getElementById('simSpec');
  const passSelect = document.getElementById('simPassive');
  const targetSelect = document.getElementById('simTarget');
  
  const baseName = baseSelect.value;
  if (!baseName) return;
  
  const char = charVariants[baseName];
  
  if (trigger === 'base') {
    // Update Spec options
    const specs = Object.keys(char.specs);
    specSelect.innerHTML = specs.map(s => `<option value="${s}">${s}</option>`).join('');
    
    // Update Passive level visibility/options
    const passWrap = document.getElementById('simPassiveWrap');
    if (char.passives.has('1lv')) {
      passWrap.style.display = 'flex';
      passSelect.innerHTML = `<option value="4lv">최대 (4레벨)</option><option value="1lv">초기 (1레벨)</option>`;
    } else {
      passWrap.style.display = 'none';
      passSelect.innerHTML = `<option value="4lv">최대 (4레벨)</option>`;
    }
  }
  
  // Update Target options based on selected Spec and Character
  const currentSpec = specSelect.value;
  const currentPass = passSelect.value;
  const variants = char.specs[currentSpec] || [];
  
  // Filter versions that match current passive
  const availableTargets = variants.filter(v => v.lv === currentPass).map(v => v.target);
  
  // Reset target select
  let targetHtml = '';
  const isEn = (LANG === 'en');
  
  if (availableTargets.includes('1') || availableTargets.includes('both')) {
    const label = isEn ? "Boss Mode (1 Unit)" : "보스전 (1인)";
    targetHtml += `<option value="1">${label}</option>`;
  }
  if (availableTargets.includes('3') || availableTargets.includes('both')) {
    const label = isEn ? "Normal Mode (3 Units)" : "일반전 (3인)";
    targetHtml += `<option value="3">${label}</option>`;
  }
    
  targetSelect.innerHTML = targetHtml || `<option value="3">${isEn ? 'Basic (3 Units)' : '기본 (3인)'}</option>`;
}

// Init
buildCharTree();
buildSidebar();
const charContainer = document.getElementById('charContainer');
charContainer.innerHTML = data.map(buildCard).join('') + `<div id="empty" class="empty-state" style="display:none;">검색 결과가 없습니다.</div>`;

// Populate simulation dropdowns
const simBaseSelect = document.getElementById('simCharBase');
const baseNames = Object.keys(charVariants);
simBaseSelect.innerHTML = baseNames.map(name => `<option value="${name}">${name}</option>`).join('');
updateSimDropdowns('base');

</script>
<script type="py">
import sys
import json
import asyncio
import datetime
import os
import base64
from js import document, console
from pyodide.ffi import create_proxy

# I18n for Simulator
LANG = "%%LANG%%"
SIM_STRINGS = {
    "ko": {
        "res_title": "[AX 특화 베스트 결과]",
        "res_opt": "최적화",
        "th_gear": "장비",
        "th_journey": "여정",
        "status_ready": "연산 시작 준비 중",
        "status_calculating": "계산 중...",
        "status_done": "모든 프로세스가 성공적으로 완료되었습니다.",
        "status_error": "오류 발생",
        "sim_run_btn": "시뮬레이션 실행"
    },
    "en": {
        "res_title": "[Best AX-Spec Results]",
        "res_opt": "Opt.",
        "th_gear": "Gear Set",
        "th_journey": "Journey",
        "status_ready": "Preparing calculation...",
        "status_calculating": "Calculating...",
        "status_done": "All processes completed successfully.",
        "status_error": "Process Failed",
        "sim_run_btn": "Run Simulation"
    }
}
S = SIM_STRINGS.get(LANG, SIM_STRINGS["ko"])

# Translation Helper for Simulator
EQUIP_MAP = %%EQUIP_MAP%%
JOURNEY_MAP = %%JOURNEY_MAP%%

def t_eq(name):
    if LANG != "en": return name
    for k, v in EQUIP_MAP.items():
        name = name.replace(k, v)
    return name

def t_jr(name):
    if LANG != "en": return name
    return JOURNEY_MAP.get(name, name)


# VFS Manual Injection (Bypass CORS for file:// protocol)
def setup_vfs():
    print("Initializing Virtual Filesystem...")
    vfs_script = document.getElementById("vfs-bundled")
    if not vfs_script:
        print("CRITICAL: VFS data not found in HTML!")
        return
    
    files = json.loads(vfs_script.innerHTML)
    for path, content in files.items():
        # Create directories if needed
        dirs = os.path.dirname(path)
        if dirs and not os.path.exists(dirs):
            os.makedirs(dirs, exist_ok=True)
            
        if content.startswith("BASE64:"):
            with open(path, "wb") as f:
                f.write(base64.b64decode(content[7:]))
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        print(f"VFS Mount: {path} ({len(content)} bytes)")

setup_vfs()

# Setup Engine
import Core.calc_engine_v5 as calc_engine
from Core.data_loader_v5 import extract_json_from_md

# Load Data inside VFS
try:
    with open("Data/characters.json", "r", encoding="utf-8") as f:
        specs = json.load(f)
except:
    specs = extract_json_from_md("Data/캐릭터_스펙_마스터.md")

rotations = extract_json_from_md("Data/사이클_로테이션_마스터.md")

def log_status(msg, is_error=False):
    status_box = document.getElementById("simStatus")
    if not status_box: return
    status_box.style.display = "block"
    color = "var(--red)" if is_error else "var(--text2)"
    now_str = datetime.datetime.now().strftime('%H:%M:%S')
    status_box.innerHTML = f"<span style='color:{color}'>[{now_str}] {msg}</span>"
    print(f"DEBUG: {msg}")

btn = document.getElementById("simBtn")
btn.querySelector(".btn-text").innerText = "시뮬레이션 실행"
btn.disabled = False
log_status("엔진 로드가 완료되었습니다. 준비 완료.")

async def run_simulation(e):
    try:
        log_status("사용자 클릭 감지 - 연산 시작 준비 중")
        btn = document.getElementById("simBtn")
        if btn: btn.disabled = True
        
        loader = document.getElementById("simLoader")
        if loader: loader.style.display = "block"
        
        btn_text = document.querySelector("#simBtn .btn-text")
        if btn_text: btn_text.innerText = S["status_calculating"]
        
        # Let UI update
        await asyncio.sleep(0.1)
        
        # Resolve selected character and parameters
        base_name = document.getElementById("simCharBase").value
        current_spec = document.getElementById("simSpec").value
        current_pass = document.getElementById("simPassive").value
        target_mode = int(document.getElementById("simTarget").value)
        
        log_status(f"Character: {base_name} ({current_spec}, {current_pass}, {target_mode}U)")
        
        # Access global JS object correctly
        import js
        variants_tree = js.window.charVariants.to_py()
        char_node = variants_tree.get(base_name)
        
        if not char_node:
            raise ValueError("캐릭터 정보를 찾을 수 없습니다.")
            
        # Find the matching RAW key
        spec_list = char_node.get("specs", {}).get(current_spec, [])
        match = None
        for v in spec_list:
            if v['lv'] == current_pass:
                # If target is filtered, we need to match it or use 'both'
                if v['target'] == 'both' or v['target'] == str(target_mode):
                    match = v['raw']
                    break
        
        if not match:
            # Fallback to the first available in this spec if no exact match
            if spec_list: match = spec_list[0]['raw']
            else: raise ValueError("해당 조합의 데이터를 찾을 수 없습니다.")
            
        char_name = match
        log_status(f"Search Key: {char_name}")
            
        cdata = specs.get(char_name)
        if not cdata:
            # Fallback 1: Try stripping common environment/passive safe IDs
            fallback_name = char_name.replace("-보스1인", "").replace("-일반3인", "")
            cdata = specs.get(fallback_name)
            if not cdata:
                # Fallback 2: Try mapping back to original keys from characters.json
                # (Simple contains check as a last resort)
                for k in specs.keys():
                    if k in char_name or char_name in k:
                        cdata = specs[k]
                        char_name = k # Use the one found
                        break
            else:
                char_name = fallback_name

        rdata = rotations.get(char_name) or rotations.get(char_name.replace("-보스1인", "").replace("-일반3인", ""))
        
        if not cdata or not rdata:
            raise ValueError(f"Data Missing for: {char_name}")
            
        char_class = cdata.get("분류", cdata.get("class", "Unknown"))
        target_count = target_mode
        
        log_status(f"Simulating... (T:{target_count}, C:{char_class})")

        # Get Substats (divided by 6 to distribute across 6 equipment slots)
        sim_vars = {
            "$ATK$": (float(document.getElementById("simAtk").value) / 100.0) / 6.0,
            "$CR$": (float(document.getElementById("simCr").value) / 100.0) / 6.0,
            "$CD$": (float(document.getElementById("simCd").value) / 100.0) / 6.0,
            "$SPD$": float(document.getElementById("simSpd").value) / 6.0
        }
        
        log_status("Binding gear...")
        calc_engine.EQUIPMENTS = calc_engine.setup_equipments(sim_vars)
        
        sim_turns = int(document.getElementById("simTurns").value)
        metric_label = "Total Dmg" if sim_turns <= 5 else "DPS"
        
        html_out = f"<h3>{S['res_title']} <span style='font-size:12px; color:var(--text3); font-weight:normal;'>({sim_turns}T {S['res_opt']})</span></h3><table class='rank-table'><thead><tr><th>{S['th_gear']}</th><th>{metric_label}</th><th>MaxHit</th><th>ATK</th><th>CR</th><th>CD</th><th>SPD</th><th>{S['th_journey']}</th></tr></thead><tbody>"
        
        # Test just the top equipment sets to save time
        eq_names = list(calc_engine.EQUIPMENTS.keys())
        best_results = []
        log_status(f"조합 탐색 시작 (전체 {len(eq_names)}개 세트 스캔)...")
        
        # Detect Moon Party environment explicitly from UI
        current_spec = document.getElementById('simSpec').value
        force_moon_party = (current_spec == '달속성 파티')
        
        for i, eq_name in enumerate(eq_names):
            if i % 2 == 0:
                log_status(f"연산 진행 중... ({i+1}/{len(eq_names)})")
                await asyncio.sleep(0.01)
                
            # Lazy Re-init check
            if not calc_engine.JOURNEYS or "Error" in calc_engine.JOURNEYS:
                log_status("데이버 베이스 재연결 시도 중...", False)
                calc_engine.JOURNEYS = calc_engine.setup_journeys()
                calc_engine.BLESSINGS = calc_engine.setup_blessings()

            res = calc_engine.find_best_journeys(char_name, char_class, cdata, rdata, eq_name, 5, (sim_turns <= 5), sim_vars, target_count, force_moon_party=force_moon_party, max_actions=sim_turns)
            # Standard contains the best for that turn count
            std_jrs, std_bless, _, _, _ = res["standard"]
            
            # Re-run for the specific turn count to get correct final metrics (redundant but safe)
            dps_final, total_final, _, _, std_max, std_stats = calc_engine.calculate_dps(char_name, cdata, rdata, eq_name, std_jrs, std_bless, sim_turns, False, target_count=target_count, force_moon_party=force_moon_party)
            std_val = total_final if sim_turns <= 5 else dps_final
            
            best_results.append((eq_name, std_bless, std_val, std_max, std_jrs, std_stats))
            
        best_results.sort(key=lambda x: x[2], reverse=True)
        log_status("연산 완료! 결과 렌더링 중...")
        
        for eq, bl, dps, mh, jrs, stats in best_results[:3]:
            jr_html = ""
            for j in jrs:
                jr_html += "<span class='j-tag'>" + t_jr(j) + "</span>"
            
            # Formatting stats
            f_atk = f"{stats.get('atk', 0):,.0f}"
            f_cr = f"{stats.get('cr', 0)*100:4.1f}%"
            f_cd = f"{stats.get('cd', 0)*100:4.1f}%"
            f_spd = f"{stats.get('spd', 0):.0f}"
            
            html_out += f"<tr><td><span class='equip-tag'>{t_eq(eq)}</span></td><td><span class='dps-val'>{dps:,.2f}</span></td><td><span class='maxhit-val'>{mh:,.0f}</span></td><td>{f_atk}</td><td>{f_cr}</td><td>{f_cd}</td><td>{f_spd}</td><td><div class='journey-list'>{jr_html}</div></td></tr>"
            
        html_out += "</tbody></table>"
        document.getElementById("simResult").innerHTML = html_out
        document.getElementById("simResult").style.display = "block"
        log_status(S["status_done"])
        
    except Exception as ex:
        log_status(f"{S['status_error']}: {str(ex)}", is_error=True)
        document.getElementById("simResult").innerHTML = f"<div style='color:red;'>{S['status_error']}: {str(ex)}</div>"
        document.getElementById("simResult").style.display = "block"
        
    if btn: btn.disabled = False
    loader = document.getElementById("simLoader")
    if loader: loader.style.display = "none"
    btn_text = document.querySelector("#simBtn .btn-text")
    if btn_text: btn_text.innerText = S["sim_run_btn"] if "sim_run_btn" in S else "Simulate"

# PyScript auto-binds helper if using py-click
pass
</script>
</body>
</html>'''


def get_vfs_bundle():
    bundle = {}
    files_to_bundle = [
        "Core/__init__.py",
        "Core/calc_engine_v5.py",
        "Core/data_loader_v5.py",
        "Core/models_v5.py",
        "Core/gear_sensitivity_v5.py",
        "Data/characters.json",
        "Data/equipments.json",
        "Data/사이클_로테이션_마스터.md",
        "Data/캐릭터_스펙_마스터.md"
    ]
    for fpath in files_to_bundle:
        full_path = os.path.join(os.path.dirname(__file__), fpath)
        if os.path.exists(full_path):
            mode = "rb"
            with open(full_path, mode) as f:
                content = f.read()
                try:
                    # Try as text first
                    bundle[fpath] = content.decode("utf-8")
                except:
                    # Fallback to base64 if it's binary or has encoding issues
                    import base64
                    bundle[fpath] = "BASE64:" + base64.b64encode(content).decode("ascii")
        else:
            print(f"Warning: Build file not found: {fpath}")
    return bundle


def generate_html(md_path: str, output_path: str, lang: str = "ko"):
    characters, update_date = parse_optimization_guide(md_path)
    
    # Translate data content if English
    if lang == "en":
        characters = translate_data_recursive(characters, lang)
        
    data_json = json.dumps(characters, ensure_ascii=False, indent=2)
    vfs_data = json.dumps(get_vfs_bundle(), ensure_ascii=False)
    
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ko"])
    
    html = HTML_TEMPLATE
    html = html.replace('%%DATA_JSON%%', data_json)
    html = html.replace('%%VFS_DATA%%', vfs_data)
    html = html.replace('%%UPDATE_DATE%%', update_date)
    html = html.replace('%%BADGE_MAP%%', json.dumps(t["badges"], ensure_ascii=False))
    
    # UI String Replacements
    html = html.replace('{{TITLE}}', t["title"])
    html = html.replace('{{HEADER_SUB}}', t["header_sub"])
    html = html.replace('{{UPDATE}}', t["update"])
    html = html.replace('{{SEARCH_PH}}', t["search_ph"])
    html = html.replace('{{SIM_TITLE}}', t["sim_title"])
    html = html.replace('{{SIM_AX_BADGE}}', t["sim_ax_badge"])
    html = html.replace('{{SIM_CHAR}}', t["sim_char"])
    html = html.replace('{{SIM_SPEC}}', t["sim_spec"])
    html = html.replace('{{SIM_PASSIVE_LV}}', t["sim_passive_lv"])
    html = html.replace('{{SIM_LV4}}', t["sim_lv4"])
    html = html.replace('{{SIM_LV1}}', t["sim_lv1"])
    html = html.replace('{{SIM_TARGET}}', t["sim_target"])
    html = html.replace('{{SIM_NORMAL}}', t["sim_normal"])
    html = html.replace('{{SIM_BOSS}}', t["sim_boss"])
    html = html.replace('{{SIM_GAUNTLET}}', t["sim_gauntlet"])
    html = html.replace('{{SIM_DURATION}}', t["sim_duration"])
    html = html.replace('{{SIM_LONG}}', t["sim_long"])
    html = html.replace('{{SIM_MID}}', t["sim_mid"])
    html = html.replace('{{SIM_SHORT}}', t["sim_short"])
    html = html.replace('{{SIM_BURST}}', t["sim_burst"])
    html = html.replace('{{SIM_ATK}}', t["sim_atk"])
    html = html.replace('{{SIM_CR}}', t["sim_cr"])
    html = html.replace('{{SIM_CD}}', t["sim_cd"])
    html = html.replace('{{SIM_SPD}}', t["sim_spd"])
    html = html.replace('{{SIM_LOADING}}', t["sim_loading"])
    html = html.replace('{{SIM_RUN}}', t["sim_run"])
    html = html.replace('{{SIDEBAR_TITLE}}', t["sidebar_title"])
    html = html.replace('{{LABEL_PEAK_DPS}}', t["label_peak_dps"])
    html = html.replace('{{LABEL_PEAK_TOTAL}}', t["label_peak_total"])
    html = html.replace('{{TAB_STD}}', t["tab_std"])
    html = html.replace('{{TAB_ALT}}', t["tab_alt"])
    html = html.replace('{{TH_RANK}}', t["th_rank"])
    html = html.replace('{{TH_GEAR}}', t["th_gear"])
    html = html.replace('{{TH_BLESS}}', t["th_bless"])
    html = html.replace('{{TH_JOURNEY}}', t["th_journey"])
    html = html.replace('{{TH_DPS}}', t["th_dps"])
    html = html.replace('{{TH_MAXHIT}}', t["th_maxhit"])
    html = html.replace('{{TRAJ_TITLE}}', t["traj_title"])
    html = html.replace('{{ALT_DESC}}', t["alt_desc"])
    html = html.replace('{{PEAK_BUILD}}', t["peak_build"])
    html = html.replace('{{LANG_NAME}}', t["lang_name"])
    html = html.replace('{{LANG_LINK}}', t["lang_link"])
    html = html.replace('{{LANG}}', lang)
    html = html.replace('%%LANG%%', lang)
    html = html.replace('%%EQUIP_MAP%%', json.dumps(DATA_TRANSLATIONS["en"]["equipments"], ensure_ascii=False))
    html = html.replace('%%JOURNEY_MAP%%', json.dumps(DATA_TRANSLATIONS["en"]["journeys"], ensure_ascii=False))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] HTML generated ({lang}): {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--md", default="Results/optimization_guide.md")
    parser.add_argument("--out", default="index.html")
    parser.add_argument("--lang", default="ko")
    args = parser.parse_args()
    
    generate_html(args.md, args.out, args.lang)
