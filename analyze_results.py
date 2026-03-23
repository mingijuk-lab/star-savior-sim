import csv
from collections import defaultdict
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

results = []
with open("Results/dps_results.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        row["DPS"] = float(row["DPS"])
        row["MaxHit"] = float(row["MaxHit"])
        results.append(row)

target_chars = [
    "벨리스",
    "샤를(바니걸)", "샤를(바니걸)(실전최적화)", "샤를(바니걸)(패시브1lv)",
    "클레어(바니걸)",
    "프레이", "프레이(달속성파티)",
    "로자리아", "로자리아(패시브1lv)",
    "유미나", "유미나(패시브1lv)",
    "레이시",
    "루나",
]

print("### 캐릭터별 최적 장비/아르카나 Top-3 (AX 여정 기준)\n")

for char in target_chars:
    char_rows = [r for r in results if r["Character"] == char]
    if not char_rows:
        continue

    ax_rows = sorted([r for r in char_rows if r["Journey"] == "AX"], key=lambda x: x["DPS"], reverse=True)
    fx_rows = sorted([r for r in char_rows if r["Journey"] == "FX"], key=lambda x: x["DPS"], reverse=True)

    print(f"#### {char}")
    print(f"| 순위 | 장비 | 아르카나 | AX DPS | FX DPS |")
    print(f"| :--- | :--- | :--- | :---: | :---: |")

    seen = []
    rank = 1
    for row in ax_rows:
        key = (row["Equip"], row["Arcana"])
        if key in seen:
            continue
        seen.append(key)
        fx_match = next((r for r in fx_rows if r["Equip"] == row["Equip"] and r["Arcana"] == row["Arcana"]), None)
        fx_dps = f'{fx_match["DPS"]:,.0f}' if fx_match else "-"
        print(f"| {rank} | {row['Equip']} | {row['Arcana']} | **{row['DPS']:,.0f}** | {fx_dps} |")
        rank += 1
        if rank > 3:
            break
    print()

# Class-level summary
print("\n---\n### 분류별 공통 추천 요약\n")
class_bests = defaultdict(list)
for char in target_chars:
    char_rows = [r for r in results if r["Character"] == char and r["Journey"] == "AX"]
    if not char_rows:
        continue
    best = max(char_rows, key=lambda x: x["DPS"])
    class_bests[best["Class"]].append((char, best["Equip"], best["Arcana"], best["DPS"]))

for cls, entries in sorted(class_bests.items()):
    print(f"**{cls}**")
    for (char, eq, arc, dps) in sorted(entries, key=lambda x: x[3], reverse=True):
        print(f"  - {char}: {eq} + {arc} → {dps:,.0f} DPS")
    print()
