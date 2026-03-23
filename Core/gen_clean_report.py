import csv
import os

def gen_good_report(csv_path='Results/dps_results.csv'):
    if not os.path.exists(csv_path):
        return

    data = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['DPS'] = float(row['DPS'])
            row['MaxHit'] = float(row['MaxHit'])
            data.append(row)

    # 1. Optimal Builds (Top 1)
    optimal = {}
    for r in data:
        c = r['Character']
        if c not in optimal or r['DPS'] > optimal[c]['DPS']:
            optimal[c] = r

    # 2. Passive Comparison
    pairs = [
        ("프레이(달속성파티)", "프레이(달속성파티, 1lv)"),
        ("로자리아", "로자리아(패시브1lv)"),
        ("유미나", "유미나(패시브1lv)"),
        ("샤를(바니걸)", "샤를(바니걸)(패시브1lv)")
    ]

    print("# 전 캐릭터 시뮬레이션 상세 리포트\n")
    print("## 1. 패시브 효율 비교")
    print("| 캐릭터 | MAX DPS | Lv.1 DPS | 효율 차이 |")
    print("| :--- | :--- | :--- | :--- |")
    for lv4, lv1 in pairs:
        if lv4 in optimal and lv1 in optimal:
            d4 = optimal[lv4]['DPS']
            d1 = optimal[lv1]['DPS']
            inc = (d4-d1)/d1*100
            print(f"| {lv4} | {d4:,.2f} | {d1:,.2f} | +{inc:.1f}% |")

    print("\n## 2. 캐릭터별 최적 세팅")
    print("| 캐릭터 | 장비 | 아르카나 | 여정 | DPS | 비고 |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    important_chars = [
        "프레이(달속성파티)", "샤를(바니걸)", "클레어(바니걸)",
        "로자리아", "유미나", "레이시", "루나", "벨리스"
    ]
    
    for cname in important_chars:
        if cname in optimal:
            o = optimal[cname]
            print(f"| {cname} | {o['Equip']} | {o['Arcana']} | {o['Journey']} | {o['DPS']:,.2f} | |")

if __name__ == "__main__":
    gen_good_report()
