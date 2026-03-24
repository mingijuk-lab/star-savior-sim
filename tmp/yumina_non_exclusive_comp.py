import csv
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extract_yumina_non_exclusive():
    results = []
    try:
        with open("Results/dps_results.csv", "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Character"] == "유미나":
                    results.append(row)
    except FileNotFoundError:
        print("Error: Results/dps_results.csv not found.")
        return

    # Filter for target builds (15 turns)
    target_turns = "15"
    arcanas = ["레인저A", "레인저B", "레인저C", "레인저D"]
    
    comparisons = []
    for row in results:
        if row["Turns"] != target_turns: continue
        if row["Arcana"] not in arcanas: continue
        if row["Journey"] not in ["AX", "GX"]: continue
        comparisons.append(row)

    # Find best Arcana for AX and GX
    best_ax = max([r for r in comparisons if r["Journey"] == "AX"], key=lambda x: float(x["DPS"]))
    best_gx = max([r for r in comparisons if r["Journey"] == "GX"], key=lambda x: float(x["DPS"]))

    print(f"### 유미나 일반 아르카나 빌드 비교 (15턴 기준)\n")
    print(f"**Best AX Build**: {best_ax['Equip']} + {best_ax['Arcana']} → {float(best_ax['DPS']):,.0f} DPS")
    print(f"**Best GX Build**: {best_gx['Equip']} + {best_gx['Arcana']} → {float(best_gx['DPS']):,.0f} DPS")
    
    diff = (float(best_ax['DPS']) / float(best_gx['DPS']) - 1) * 100
    print(f"\n최적 일반 아르카나에서도 **AX 빌드가 GX 빌드보다 {diff:.2f}% 더 강력**합니다.")

    # Table of all general Arcanas (AX only for simplicity, or both)
    # Let's show the best for each Arcana
    print("\n| 아르카나 | 장비(AX) | AX DPS | GX DPS |")
    print("| :--- | :--- | :---: | :---: |")
    
    memo = {} # arc: {AX: dps, GX: dps, eq: eq}
    for r in comparisons:
        arc = r["Arcana"]
        jr = r["Journey"]
        dps = float(r["DPS"])
        if arc not in memo: memo[arc] = {"AX": 0, "GX": 0, "eq": ""}
        if dps > memo[arc][jr]:
             memo[arc][jr] = dps
             if jr == "AX": memo[arc]["eq"] = r["Equip"]
             
    for arc, data in sorted(memo.items()):
        print(f"| {arc} | {data['eq']} | {data['AX']:,.0f} | {data['GX']:,.0f} |")

if __name__ == "__main__":
    extract_yumina_non_exclusive()
