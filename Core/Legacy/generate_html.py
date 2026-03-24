import csv
import json
from collections import defaultdict

# Read results
results = []
try:
    with open('Results/dps_results.csv', mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append({
                'Character': row['Character'],
                'Class': row['Class'],
                'Equipment': row['Equip'],
                'Arcana': row['Arcana'],
                'Journey': row['Journey'],
                'Turns': row['Turns'],
                'DPS': float(row['DPS']),
                'MaxHit': float(row['MaxHit'])
            })
except Exception as e:
    print(f"Error reading file: {e}")

# Group by (Character, Turns) and take Top 1
char_turns_groups = defaultdict(lambda: defaultdict(list))
for r in results:
    char_turns_groups[r['Character']][r['Turns']].append(r)

top_results = {}
for char, turns_dict in char_turns_groups.items():
    top_results[char] = {}
    for turns, items in turns_dict.items():
        top_results[char][turns] = max(items, key=lambda x: x['DPS'])

html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Star Savior DPS Leaderboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        body {
            font-family: 'Inter', sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
        }
        .glass-panel {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
        }
        .card-hover {
            transition: all 0.3s ease;
        }
        .card-hover:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3);
            border-color: #3b82f6;
        }
        .gradient-text {
            background: linear-gradient(135deg, #60a5fa, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
    </style>
</head>
<body class="min-h-screen p-8">
    <div class="max-w-7xl mx-auto">
        <header class="text-center mb-12">
            <h1 class="text-5xl font-bold gradient-text mb-4">Star Savior DPS Leaderboard</h1>
            <p class="text-slate-400 text-lg">캐릭터별 최적화 장비, 아르카나, 여정 조합 시뮬레이션 결과</p>
        </header>
        
        <!-- Chart Section -->
        <div class="glass-panel p-6 mb-12 shadow-2xl">
            <div class="h-[400px]">
                <canvas id="dpsChart"></canvas>
            </div>
        </div>
        
        <!-- Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
"""

arcana_details = {
    "어쌔신": "공+14% / 치확+30% / 턴시작 속도+10(최대3회) [대상: 어쌔신]",
    "스트라이커A": "공+14% / 치확+30% / 특수기DMG+5%(최대5회) [대상: 일반]",
    "스트라이커B": "공+14% / 치확+30% / 속도+8 [대상: 일반]",
    "스트라이커C": "공+14% / 치확+24% / 특수기DMG+5%(최대5회), 치피+12% [대상: 일반]",
    "스트라이커D": "공+6% / 치확+30% / 특수기DMG+5%(최대5회), 치피+12% [대상: 일반]",
    "캐스터A": "공+14% / 치확+30% / 턴시작 치피+10%(최대3회) [대상: 캐스터]",
    "캐스터B": "공+8% / 치확+30% / 턴시작 치피+10%(3회) + 특수기DMG+5%(5스택) [대상: 캐스터]",
    "캐스터C": "공+8% / 치확+24% / 턴시작 치피+10%(3회) + 특수기DMG+5%(5스택), 치피+12% [대상: 캐스터]",
    "레인저A": "공+6% / 치확+24% / 피증+12% / 조건부 치확+5%, 타겟당 공+3% [대상: 레인저]",
    "레인저B": "공+6% / 치확+24% / 특수기DMG+5% / 조건부 치확+5%, 치피+12% [대상: 레인저]",
    "레인저C": "공+6% / 치확+24% / 조건부 특수기DMG+5%, 타겟당 공+3%, 조건부 치확+5% [대상: 레인저]",
    "레인저D": "공+0% / 치확+18% / 피증+12% / 조건부 특수기DMG+5%, 타겟당 공+3%, 조건부 치확+5% [대상: 레인저]",
}

equip_details = {
    "공격4": "공격력 +20% / 기본부옵: 공+16.25%, 속도+60",
    "통찰4": "치확 +30% / 기본부옵: 공+16.25%, 속도+60",
    "파괴4": "치피 +40% / 기본부옵: 공+16.25%, 속도+60",
    "속도4": "속도 +15 / 기본부옵: 공+16.25%, 속도+75",
}

journey_details = {
    "AX": "공격력+8% / 턴시작 공격력+8%(최대5회), 궁극기시 초기화 (폭발력)",
    "FX": "치피+10% / 치명타시 다음 타격 DI+25% (연속성)",
    "EX": "치확+10% / 기본기 치명타시 25%확률 팀원 기본기 (협공)",
}

class_colors = {
    "레인저": "bg-green-900/40 text-green-400 border-green-800",
    "캐스터": "bg-purple-900/40 text-purple-400 border-purple-800",
    "스트라이커": "bg-red-900/40 text-red-400 border-red-800",
    "어쌔신": "bg-slate-900/40 text-slate-400 border-slate-800",
}

sorted_chars = sorted(top_results.keys(), key=lambda k: top_results[k].get('15', {}).get('DPS', 0), reverse=True)

for char in sorted_chars:
    char_data = top_results[char]
    if not char_data: continue
    
    # Get class from any of the results
    char_class = next(iter(char_data.values()))['Class']
    class_style = class_colors.get(char_class, "bg-slate-800 text-slate-300 border-slate-700")
    
    html_content += f"""
            <div class="glass-panel p-6 card-hover flex flex-col">
                <div class="flex justify-between items-start mb-4 pb-3 border-b border-slate-700">
                    <h2 class="text-2xl font-bold text-slate-100">{char}</h2>
                    <span class="text-xs px-2 py-1 rounded border {class_style}">{char_class}</span>
                </div>
                <div class="space-y-4">
    """
    
    for t_val in ["5", "10", "15"]:
        if t_val not in char_data: continue
        item = char_data[t_val]
        
        # Determine rank appearance or just labeling
        label_color = "text-blue-400" if t_val == "5" else ("text-purple-400" if t_val == "10" else "text-emerald-400")
        
        eq_name = item['Equipment'].replace("세트", "").strip()
        arc_key = item['Arcana'].split(" ")[0] if item['Arcana'] else ""
        eq_title = equip_details.get(eq_name, item['Equipment'])
        arc_title = arcana_details.get(arc_key, item['Arcana'])
        jour_title = journey_details.get(item['Journey'], item['Journey'])
        
        html_content += f"""
                    <div class="bg-slate-800/60 rounded-xl p-4 flex flex-col gap-2">
                        <div class="flex items-center justify-between mb-1">
                            <span class="text-xs font-black {label_color} uppercase tracking-tighter">{t_val} TURNS OPTIMAL</span>
                        </div>
                        <div class="flex gap-1 overflow-hidden mb-1">
                            <span title="{eq_title}" class="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300 cursor-help truncate">{item['Equipment']}</span>
                            <span title="{arc_title}" class="text-[10px] px-1.5 py-0.5 rounded bg-blue-900/30 border border-blue-800 text-blue-300 cursor-help truncate">{item['Arcana']}</span>
                            <span title="{jour_title}" class="text-[10px] px-1.5 py-0.5 rounded bg-purple-900/30 border border-purple-800 text-purple-300 cursor-help truncate">{item['Journey']}</span>
                        </div>
                        <div class="flex justify-between items-end">
                            <div>
                                <div class="text-[9px] text-slate-500 uppercase tracking-widest font-bold">Avg DPS</div>
                                <div class="text-lg font-bold text-blue-400 leading-none">{item['DPS']:,.0f}</div>
                            </div>
                            <div class="text-right">
                                <div class="text-[9px] text-slate-500 uppercase tracking-widest font-bold">Max Hit</div>
                                <div class="text-xs font-semibold text-slate-400 leading-none">{item['MaxHit']:,.0f}</div>
                            </div>
                        </div>
                    </div>
        """
    html_content += """
                </div>
            </div>
    """

char_labels = []
top15_dps = []
top5_dps = []
for char in sorted_chars:
    char_data = top_results[char]
    char_labels.append(char)
    top15_dps.append(char_data.get("15", {}).get("DPS", 0))
    top5_dps.append(char_data.get("5", {}).get("DPS", 0))

# Add Glossary Section
html_content += """
        </div>

        <!-- Glossary Section -->
        <div class="glass-panel p-8 mb-12">
            <h2 class="text-3xl font-bold mb-8 text-slate-100 flex items-center">
                <span class="w-8 h-8 bg-blue-600 rounded mr-3 flex items-center justify-center text-sm">ⓘ</span>
                세부 정보 가이드 (아르카나 / 장비 / 여정)
            </h2>
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <!-- Arcana -->
                <div>
                    <h3 class="text-blue-400 font-bold mb-4 flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-blue-400"></span> 아르카나 (Arcana)
                    </h3>
                    <div class="space-y-3">
"""
for name, desc in arcana_details.items():
    html_content += f"""
                        <div class="text-sm">
                            <span class="font-bold text-slate-300 block mb-1">{name}</span>
                            <span class="text-slate-500 text-xs leading-relaxed">{desc}</span>
                        </div>
    """

html_content += """
                    </div>
                </div>
                <!-- Equipment -->
                <div>
                    <h3 class="text-emerald-400 font-bold mb-4 flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-400"></span> 장비 (Equipment)
                    </h3>
                    <div class="space-y-3">
"""
for name, desc in equip_details.items():
    html_content += f"""
                        <div class="text-sm">
                            <span class="font-bold text-slate-300 block mb-1">{name}</span>
                            <span class="text-slate-500 text-xs leading-relaxed">{desc}</span>
                        </div>
    """
html_content += """
                    </div>
                </div>
                <!-- Journey -->
                <div>
                    <h3 class="text-purple-400 font-bold mb-4 flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-purple-400"></span> 여정 (Journey)
                    </h3>
                    <div class="space-y-3">
"""
for name, desc in journey_details.items():
    html_content += f"""
                        <div class="text-sm">
                            <span class="font-bold text-slate-300 block mb-1">{name}</span>
                            <span class="text-slate-500 text-xs leading-relaxed">{desc}</span>
                        </div>
    """
html_content += """
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const ctx = document.getElementById('dpsChart').getContext('2d');
        
        const gradient1 = ctx.createLinearGradient(0, 0, 0, 400);
        gradient1.addColorStop(0, 'rgba(59, 130, 246, 1)'); 
        gradient1.addColorStop(1, 'rgba(59, 130, 246, 0.2)');
        
        const gradient2 = ctx.createLinearGradient(0, 0, 0, 400);
        gradient2.addColorStop(0, 'rgba(168, 85, 247, 0.8)'); 
        gradient2.addColorStop(1, 'rgba(168, 85, 247, 0.1)');

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: """ + json.dumps(char_labels) + """,
                datasets: [
                    {
                        label: '15턴 최적 DPS',
                        data: """ + json.dumps(top15_dps) + """,
                        backgroundColor: gradient1,
                        borderColor: '#3b82f6',
                        borderWidth: 1,
                        borderRadius: 6,
                        barPercentage: 0.8,
                        categoryPercentage: 0.8
                    },
                    {
                        label: '5턴 최적 DPS',
                        data: """ + json.dumps(top5_dps) + """,
                        backgroundColor: gradient2,
                        borderColor: '#a855f7',
                        borderWidth: 1,
                        borderRadius: 6,
                        barPercentage: 0.8,
                        categoryPercentage: 0.8
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: { 
                        labels: { 
                            color: '#e2e8f0',
                            font: { family: "'Inter', sans-serif", size: 14 }
                        } 
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#f8fafc',
                        bodyColor: '#cbd5e1',
                        borderColor: '#334155',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(51, 65, 85, 0.5)', drawBorder: false },
                        ticks: { 
                            color: '#94a3b8',
                            font: { family: "'Inter', sans-serif" }
                        }
                    },
                    x: {
                        grid: { display: false, drawBorder: false },
                        ticks: { 
                            color: '#e2e8f0',
                            font: { family: "'Inter', sans-serif", size: 12 },
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""

with open('Results/dps_results.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
print("HTML Generated!")
