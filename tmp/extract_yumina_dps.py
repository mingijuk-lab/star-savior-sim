import csv
import sys
import io

# Force stdout to use utf-8 to avoid mangling in some environments
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extract_yumina_dps():
    results = []
    try:
        with open("Results/dps_results.csv", "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Character"] == "유미나" and row["Arcana"] == "레인저(유미나 전용)":
                    results.append(row)
    except FileNotFoundError:
        print("Error: Results/dps_results.csv not found.")
        return

    # Filter for target builds (15 turns is the most representative for long-term DPS)
    target_turns = "15"
    
    comparisons = []
    
    for row in results:
        if row["Turns"] != target_turns: continue
        jr = row["Journey"]
        if jr not in ["AX", "GX"]: continue
        
        comparisons.append(row)

    # Group by equipment
    by_eq = {} # {eq: {AX: dps, GX: dps}}
    for row in comparisons:
        eq = row["Equip"]
        jr = row["Journey"]
        dps = float(row["DPS"])
        if eq not in by_eq: by_eq[eq] = {"AX": 0, "GX": 0}
        by_eq[eq][jr] = dps

    print(f"### 유미나 여정별 DPS 비교 (15턴 기준, 전용 아르카나 고정)\n")
    print("| 장비 세트 | AX (표준) | GX (출혈) | 차이 (GX vs AX) |")
    print("| :--- | :---: | :---: | :---: |")
    
    # Sort by AX DPS descending
    sorted_eq = sorted(by_eq.items(), key=lambda x: x[1]["AX"], reverse=True)
    
    for eq, data in sorted_eq:
        ax = data["AX"]
        gx = data["GX"]
        diff = ((gx - ax) / ax * 100) if ax > 0 else 0
        print(f"| {eq} | {ax:,.0f} | {gx:,.0f} | {diff:+.2f}% |")

if __name__ == "__main__":
    extract_yumina_dps()
