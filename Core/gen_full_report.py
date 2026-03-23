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
    
    # 1. Optimal Builds by Character
    optimal_builds = {}
    for r in data:
        c = r['Character']
        if c not in optimal_builds or r['DPS'] > optimal_builds[c]['DPS']:
            optimal_builds[c] = r
            
    # 2. Passive Level Comparisons
    # Pairs: (Lv4_Name, Lv1_Name)
    pairs = [
        ("프레이(달속성파티)", "프레이(달속성파티, 1lv)"),
        ("로자리아", "로자리아(패시브1lv)"),
        ("유미나", "유미나(패시브1lv)"),
        ("샤를(바니걸)", "샤를(바니걸)(패시브1lv)")
    ]
    
    passive_comp = []
    for lv4, lv1 in pairs:
        if lv4 in optimal_builds and lv1 in optimal_builds:
            dps4 = optimal_builds[lv4]['DPS']
            dps1 = optimal_builds[lv1]['DPS']
            diff = (dps4 - dps1) / dps1 * 100
            passive_comp.append({
                "Character": lv4,
                "Lv4_DPS": dps4,
                "Lv1_DPS": dps1,
                "Increase": f"{diff:.1f}%"
            })

    # Output Generation
    print("# Full Simulation Analysis Report\n")
    
    print("## 1. Character Passive Level Comparison (Lv1 vs Max)")
    print("| Character | Max Lv DPS | Lv1 DPS | Difference |")
    print("| :--- | :--- | :--- | :--- |")
    for pc in passive_comp:
        print(f"| {pc['Character']} | {pc['Lv4_DPS']:,} | {pc['Lv1_DPS']:,} | +{pc['Increase']} |")
        
    print("\n## 2. Optimal Builds (Top 1 for each Character)")
    print("| Character | Equipment | Arcana | Journey | DPS | MaxHit |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for c in characters:
        if "1lv" in c: continue # Skip Lv 1 in the general optimal list if needed or keep both
        b = optimal_builds[c]
        print(f"| {c} | {b['Equip']} | {b['Arcana']} | {b['Journey']} | {b['DPS']:,} | {b['MaxHit']:,} |")

if __name__ == "__main__":
    analyze_all()
