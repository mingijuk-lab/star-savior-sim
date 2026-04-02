#!/usr/bin/env python3
"""
generate_html.py — optimization_guide.md → HTML 변환기
시각화 가이드(Docs/시각화_가이드.md)에 정의된 규격에 따라 동작합니다.
"""
import re
import json
import sys

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
    name = raw_name
    badges = []

    # Extract base name
    base = re.sub(r'\(.*?\)', '', raw_name).strip()
    name = base

    paren_content = re.findall(r'\(([^)]+)\)', raw_name)
    for p in paren_content:
        if '달속성파티' in p: badges.append('moon')
        if '바니걸' in p: badges.append('bunny')
        if '패시브1lv' in p or '패시브1lv' in p: badges.append('passive')
        if '궁극기미사용' in p: badges.append('noult')
        if '보스1인' in p: badges.append('boss')
        if '일반3인' in p: badges.append('normal')

    # Sanitize ID (Include suffixes to prevent card collision)
    safe_id = raw_name.replace('(', '-').replace(')', '').replace(',', '').replace(' ', '-').replace('1lv', '1lv')

    # Parse Standard Strategy table
    std_ranks = []
    std_traj = []
    alt_data = None

    # Find Standard table rows: look for lines with "| 1 |", "| 2 |", "| 3 |"
    table_pattern = re.compile(
        r'\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*\*\*([0-9,.]+)\*\*\s*\|\s*([0-9,.]+)\s*\|'
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

            # Parse journey names (separated by | within the cell)
            journeys = [j.strip() for j in journeys_raw.split('|') if j.strip()]

            std_ranks.append({
                "rank": rank,
                "equip": equip,
                "bless": bless,
                "journeys": journeys,
                "dps": dps,
                "maxHit": max_hit
            })

    # Parse No-Ult peak row
    alt_pattern = re.compile(
        r'\|\s*\*\*최고점\*\*\s*\|\s*(.+?)\s*\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*\*\*([0-9,.]+)\*\*\s*\|\s*([0-9,.]+)\s*\|'
    )
    for line in lines:
        m = alt_pattern.search(line)
        if m:
            equip = m.group(1).strip()
            bless = m.group(2).strip()
            journeys_raw = m.group(3).strip()
            dps = float(m.group(4).replace(',', ''))
            max_hit = int(float(m.group(5).replace(',', '')))
            journeys = [j.strip() for j in journeys_raw.split('|') if j.strip()]

            alt_data = {
                "equip": equip,
                "bless": bless,
                "journeys": journeys,
                "dps": dps,
                "maxHit": max_hit
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
        "name": name,
        "badges": badges,
        "peakDPS": peak_dps,
        "maxHit": peak_max_hit,
        "std": {
            "ranks": std_ranks,
            "traj": std_traj
        },
        "alt": alt_data or {"equip": "N/A", "bless": "N/A", "journeys": [], "dps": 0, "maxHit": 0}
    }


HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>스타 세이비어 — 최적화 가이드</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0c10;
    --bg2: #0f1218;
    --bg3: #161b24;
    --bg4: #1d2330;
    --border: #242c3a;
    --border2: #2e3a4e;
    --gold: #f0b429;
    --gold2: #e8a000;
    --blue: #4a9eff;
    --blue2: #2b7fe0;
    --red: #ff5757;
    --green: #3ecf8e;
    --purple: #9b72ff;
    --orange: #ff8c42;
    --text: #e8ecf1;
    --text2: #9aa5b4;
    --text3: #637285;
    --rank1: #f0b429;
    --rank2: #9aa5b4;
    --rank3: #cd7c3e;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Noto Sans KR', sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
  }

  header {
    position: sticky; top: 0; z-index: 100;
    background: rgba(10,12,16,0.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    display: flex; align-items: center; gap: 16px; height: 56px;
  }
  .logo { font-size: 13px; font-weight: 700; letter-spacing: 0.15em; color: var(--gold); text-transform: uppercase; white-space: nowrap; }
  .header-sep { flex: 1; }
  .update-badge { font-size: 11px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }

  .search-wrap { padding: 20px 24px 0; max-width: 1400px; margin: 0 auto; }
  .search-box { position: relative; width: 100%; max-width: 480px; }
  .search-box input {
    width: 100%; background: var(--bg3); border: 1px solid var(--border2);
    color: var(--text); padding: 10px 16px 10px 40px; border-radius: 8px;
    font-size: 14px; font-family: 'Noto Sans KR', sans-serif; outline: none;
    transition: border-color 0.2s;
  }
  .search-box input:focus { border-color: var(--blue); }
  .search-box input::placeholder { color: var(--text3); }
  .search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text3); font-size: 16px; pointer-events: none; }

  .layout { display: flex; max-width: 1400px; margin: 0 auto; padding: 20px 24px 60px; gap: 24px; align-items: flex-start; }

  .sidebar {
    width: 220px; flex-shrink: 0; position: sticky; top: 72px;
    max-height: calc(100vh - 90px); overflow-y: auto;
    scrollbar-width: thin; scrollbar-color: var(--border2) transparent;
  }
  .sidebar::-webkit-scrollbar { width: 4px; }
  .sidebar::-webkit-scrollbar-track { background: transparent; }
  .sidebar::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
  .sidebar-title { font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text3); font-weight: 700; padding: 0 0 10px; border-bottom: 1px solid var(--border); margin-bottom: 8px; }
  .nav-item { display: block; padding: 6px 10px; border-radius: 6px; font-size: 13px; color: var(--text2); cursor: pointer; transition: all 0.15s; line-height: 1.4; border: none; background: none; text-align: left; width: 100%; }
  .nav-item:hover { background: var(--bg3); color: var(--text); }
  .nav-item.active { background: rgba(74,158,255,0.12); color: var(--blue); }

  .main { flex: 1; min-width: 0; }

  .char-card { background: var(--bg2); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 16px; overflow: hidden; transition: border-color 0.2s; }
  .char-card.hidden { display: none; }
  .char-header { display: flex; align-items: center; padding: 16px 20px; cursor: pointer; gap: 12px; user-select: none; background: var(--bg3); transition: background 0.15s; }
  .char-header:hover { background: var(--bg4); }
  .char-name { font-size: 17px; font-weight: 700; flex: 1; }
  .char-badge { font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: 500; letter-spacing: 0.04em; }
  .badge-moon { background: rgba(155,114,255,0.15); color: var(--purple); border: 1px solid rgba(155,114,255,0.3); }
  .badge-bunny { background: rgba(255,140,66,0.12); color: var(--orange); border: 1px solid rgba(255,140,66,0.25); }
  .badge-passive { background: rgba(158,165,180,0.1); color: var(--text2); border: 1px solid var(--border2); }
  .badge-noult { background: rgba(255,87,87,0.1); color: var(--red); border: 1px solid rgba(255,87,87,0.25); }
  .badge-boss { background: rgba(255,215,0,0.1); color: var(--gold); border: 1px solid rgba(240,180,41,0.3); }
  .badge-normal { background: rgba(74,158,255,0.1); color: var(--blue); border: 1px solid rgba(74,158,255,0.3); }

  .dps-peak { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: var(--gold); }
  .dps-label { font-size: 10px; color: var(--text3); margin-right: 4px; }
  .chevron { font-size: 12px; color: var(--text3); transition: transform 0.2s; }
  .char-card.open .chevron { transform: rotate(180deg); }
  .char-body { display: none; padding: 0 20px 20px; }
  .char-card.open .char-body { display: block; }

  .strat-tabs { display: flex; gap: 4px; margin: 16px 0 12px; background: var(--bg); border-radius: 8px; padding: 4px; width: fit-content; }
  .strat-tab { padding: 6px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.15s; border: none; background: none; color: var(--text3); letter-spacing: 0.03em; }
  .strat-tab.active-std { background: rgba(74,158,255,0.15); color: var(--blue); }
  .strat-tab.active-alt { background: rgba(255,87,87,0.12); color: var(--red); }
  .strat-tab:not(.active-std):not(.active-alt):hover { color: var(--text2); background: var(--bg3); }
  .strat-panel { display: none; }
  .strat-panel.visible { display: block; }

  .rank-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 16px; }
  .rank-table th { padding: 8px 10px; text-align: left; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text3); font-weight: 600; border-bottom: 1px solid var(--border); }
  .rank-table td { padding: 10px 10px; border-bottom: 1px solid rgba(36,44,58,0.5); vertical-align: middle; }
  .rank-table tr:last-child td { border-bottom: none; }
  .rank-table tr:hover td { background: rgba(255,255,255,0.02); }

  .rank-num { font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 700; width: 32px; }
  .rank-1 { color: var(--rank1); }
  .rank-2 { color: var(--rank2); }
  .rank-3 { color: var(--rank3); }

  .equip-tag { display: inline-block; font-size: 11px; padding: 2px 7px; border-radius: 4px; background: var(--bg4); color: var(--text2); font-family: 'JetBrains Mono', monospace; white-space: nowrap; }
  .bless-tag { display: inline-block; font-size: 11px; padding: 2px 6px; border-radius: 3px; background: rgba(240,180,41,0.1); color: var(--gold); font-weight: 700; border: 1px solid rgba(240,180,41,0.2); }

  .journey-list { display: flex; flex-wrap: wrap; gap: 4px; }
  .j-tag { font-size: 11px; padding: 2px 7px; border-radius: 4px; background: rgba(74,158,255,0.08); color: var(--blue); border: 1px solid rgba(74,158,255,0.18); white-space: nowrap; }

  .dps-val { font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 700; color: var(--green); white-space: nowrap; }
  .maxhit-val { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: var(--gold); white-space: nowrap; }

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
</style>
</head>
<body>

<header>
  <div class="logo">⭐ Star Savior</div>
  <span style="color:var(--text3);font-size:13px;">구원자 최적화 가이드</span>
  <div class="header-sep"></div>
  <div class="update-badge">업데이트: %%UPDATE_DATE%%</div>
</header>

<div class="search-wrap">
  <div class="search-box">
    <span class="search-icon">🔍</span>
    <input type="text" id="searchInput" placeholder="캐릭터 이름으로 검색..." oninput="filterChars()">
  </div>
</div>

<div class="layout">
  <nav class="sidebar" id="sidebar"></nav>
  <main class="main" id="main"></main>
</div>

<script>
const data = %%DATA_JSON%%;

const badgeMap = {
  moon: { cls:"badge-moon", label:"달속성 파티" },
  bunny: { cls:"badge-bunny", label:"바니걸" },
  passive: { cls:"badge-passive", label:"패시브 1lv" },
  noult: { cls:"badge-noult", label:"궁극기 미사용" },
  boss: { cls:"badge-boss", label:"보스 1인" },
  normal: { cls:"badge-normal", label:"일반 3인" },
};

function renderBadges(badges) {
  return badges.map(b => `<span class="char-badge ${badgeMap[b].cls}">${badgeMap[b].label}</span>`).join('');
}
function journeyTags(js) {
  return js.map(j => `<span class="j-tag">${j}</span>`).join('');
}
function trajJourneyTags(js) {
  return js.map(j => `<span class="tj">${j}</span>`).join('');
}
function fmt(n) { return n.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2}); }
function fmtInt(n) { return n.toLocaleString(); }

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
        <span class="dps-label">최고 DPS</span><span class="dps-peak">${fmt(char.peakDPS)}</span>
        <span class="chevron">▼</span>
      </div>
    </div>
    <div class="char-body">
      <div class="strat-tabs">
        <button class="strat-tab active-std" id="tab-std-${char.id}" onclick="switchTab('${char.id}','std')">🔹 일반 전략 (궁극기 사용)</button>
        <button class="strat-tab" id="tab-alt-${char.id}" onclick="switchTab('${char.id}','alt')">🔸 노울트 전략 (AX 특화)</button>
      </div>

      <div class="strat-panel visible" id="${stdId}">
        <table class="rank-table">
          <thead>
            <tr>
              <th>순위</th><th>장비 세트</th><th>축복</th><th>최적 여정 조합 (Top 5)</th><th>DPS (15T)</th><th>MaxHit</th>
            </tr>
          </thead>
          <tbody>${rankRows}</tbody>
        </table>
        <div class="traj-section">
          <div class="traj-title">빌드 진화 경로</div>
          ${trajSections}
        </div>
      </div>

      <div class="strat-panel" id="${altId}">
        <div style="font-size:12px;color:var(--text3);margin-bottom:12px;">궁극기를 포기하고 AX 스택 피해량에 올인한 특수 상황용 고점 빌드입니다.</div>
        <div class="peak-box">
          <span class="peak-label">최고점</span>
          <span class="peak-equip"><span class="equip-tag">${char.alt.equip}</span>&nbsp;<span class="bless-tag">${char.alt.bless}</span></span>
          <div class="traj-journeys" style="flex:1;margin-left:8px;">${trajJourneyTags(char.alt.journeys)}</div>
          <span class="peak-maxhit">💥${fmtInt(char.alt.maxHit)}</span>
          <span class="peak-dps">${fmt(char.alt.dps)}</span>
        </div>
      </div>
    </div>
  </div>`;
}

function buildSidebar() {
  const sidebar = document.getElementById('sidebar');
  let html = `<div class="sidebar-title">구원자 목록</div>`;
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

// Init
buildSidebar();
const main = document.getElementById('main');
main.innerHTML = data.map(buildCard).join('') + `<div id="empty" class="empty-state" style="display:none;">검색 결과가 없습니다.</div>`;
</script>
</body>
</html>'''


def generate_html(md_path: str, output_path: str):
    characters, update_date = parse_optimization_guide(md_path)

    data_json = json.dumps(characters, ensure_ascii=False, indent=2)

    html = HTML_TEMPLATE.replace('%%DATA_JSON%%', data_json)
    html = html.replace('%%UPDATE_DATE%%', update_date)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] HTML generated: {output_path}")
    print(f"     Characters: {len(characters)}")
    print(f"     Update date: {update_date}")


if __name__ == "__main__":
    md_input = sys.argv[1] if len(sys.argv) > 1 else "Results/optimization_guide.md"
    html_output = sys.argv[2] if len(sys.argv) > 2 else "Results/optimization_guide.html"
    generate_html(md_input, html_output)
