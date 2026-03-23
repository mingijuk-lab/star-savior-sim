import csv
import sys
import os

def compare_character(cname, csv_path='Results/dps_results.csv'):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    results = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if cname in row['Character']:
                row['DPS'] = float(row['DPS'])
                row['MaxHit'] = float(row['MaxHit'])
                results.append(row)

    if not results:
        print(f"No results found for character: {cname}")
        return

    # Sort by DPS descending
    results.sort(key=lambda x: x['DPS'], reverse=True)

    print(f"# Comparison for {cname}")
    print("\n## Top 5 Builds")
    print("| Rank | Equipment | Arcana | Journey | DPS | MaxHit | % of Max |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    max_dps = results[0]['DPS']
    for i, r in enumerate(results[:10]):
        pct = (r['DPS'] / max_dps) * 100
        print(f"| {i+1} | {r['Equip']} | {r['Arcana']} | {r['Journey']} | {r['DPS']:,} | {r['MaxHit']:,} | {pct:.1f}% |")

    # Group by Equipment
    print("\n## Best DPS by Equipment Set")
    equip_best = {}
    for r in results:
        eq = r['Equip']
        if eq not in equip_best or r['DPS'] > equip_best[eq]['DPS']:
            equip_best[eq] = r
    
    sorted_equips = sorted(equip_best.values(), key=lambda x: x['DPS'], reverse=True)
    print("| Equipment | Best DPS | Arcana | Journey |")
    print("| :--- | :--- | :--- | :--- |")
    for r in sorted_equips:
        print(f"| {r['Equip']} | {r['DPS']:,} | {r['Arcana']} | {r['Journey']} |")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else ""
    if not target:
        print("Usage: python Core/compare_builds.py <CharacterName>")
    else:
        compare_character(target)
