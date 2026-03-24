import csv
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extract_luna_peak():
    results = []
    try:
        with open("Results/dps_results.csv", "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Character"] == "루나":
                    results.append(row)
    except FileNotFoundError:
        print("Error: Results/dps_results.csv not found.")
        return

    # Sort by MaxHit descending
    sorted_hits = sorted(results, key=lambda x: float(x["MaxHit"]), reverse=True)

    print(f"### 루나 궁극기/최대 한방 딜 (MaxHit) Top-10\n")
    print("| 순위 | 장비 | 아르카나 | 여정 | MaxHit | DPS |")
    print("| :--- | :--- | :--- | :--- | :---: | :---: |")
    
    seen = set()
    rank = 1
    for row in sorted_hits:
        key = (row["Equip"], row["Arcana"], row["Journey"])
        if key in seen: continue
        seen.add(key)
        
        print(f"| {rank} | {row['Equip']} | {row['Arcana']} | {row['Journey']} | **{float(row['MaxHit']):,.0f}** | {float(row['DPS']):,.0f} |")
        rank += 1
        if rank > 10: break

if __name__ == "__main__":
    extract_luna_peak()
