import csv
import os

def analyze_all(csv_path='Results/dps_results.csv'):
    if not os.path.exists(csv_path):
        return "File not found"

    data = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['DPS'] = float(row['DPS'])
            row['MaxHit'] = float(row['MaxHit'])
            data.append(row)

    characters = sorted(list(set(r['Character'] for r in data)))
    
    # 1. Optimal Builds by Character and Turns
    optimal_builds = {} # key: (Character, Turns)
    for r in data:
        key = (r['Character'], r['Turns'])
        if key not in optimal_builds or r['DPS'] > optimal_builds[key]['DPS']:
            optimal_builds[key] = r
            
    # 2. Passive Level Comparisons (at 15 turns)
    pairs = [
        ("프레이(달속성파티)", "프레이(달속성파티, 1lv)"),
        ("로자리아", "로자리아(패시브1lv)"),
        ("유미나", "유미나(패시브1lv)"),
        ("샤를(바니걸)", "샤를(바니걸)(패시브1lv)")
    ]
    
    passive_comp = []
    for lv4, lv1 in pairs:
        key4 = (lv4, "15")
        key1 = (lv1, "15")
        if key4 in optimal_builds and key1 in optimal_builds:
            dps4 = optimal_builds[key4]['DPS']
            dps1 = optimal_builds[key1]['DPS']
            diff = (dps4 - dps1) / dps1 * 100
            passive_comp.append({
                "Character": lv4,
                "Lv4_DPS": dps4,
                "Lv1_DPS": dps1,
                "Increase": f"{diff:.1f}%"
            })

    # Output Generation
    lines = []
    lines.append("# Full Simulation Analysis Report (5/10/15 Turns)\n")
    
    lines.append("## 1. Character Passive Level Comparison (15 Turns)")
    lines.append("| Character | Max Lv DPS | Lv1 DPS | Difference |")
    lines.append("| :--- | :--- | :--- | :--- |")
    for pc in passive_comp:
        lines.append(f"| {pc['Character']} | {pc['Lv4_DPS']:,} | {pc['Lv1_DPS']:,} | +{pc['Increase']} |")
        
    lines.append("\n## 2. Optimal Builds by Combat Length")
    for t in ["5", "10", "15"]:
        lines.append(f"\n### combat_length: {t} turns")
        lines.append("| Character | Equipment | Arcana | Journey | DPS | MaxHit |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for c in characters:
            if "1lv" in c: continue
            key = (c, t)
            if key in optimal_builds:
                b = optimal_builds[key]
                lines.append(f"| {c} | {b['Equip']} | {b['Arcana']} | {b['Journey']} | {b['DPS']:,} | {b['MaxHit']:,} |")

    content = "\n".join(lines)
    print(content)
    
    with open("Results/summary_report.md", "w", encoding="utf-8-sig") as f:
        f.write(content)

if __name__ == "__main__":
    analyze_all()
