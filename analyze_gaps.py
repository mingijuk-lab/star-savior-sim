import pandas as pd

def analyze_dps_gaps():
    try:
        df = pd.read_csv("Results/dps_results.csv")
        
        # Filter for 15 turns
        df_15 = df[df["Turns"] == 15]
        
        # Get max DPS per character
        max_dps = df_15.groupby("Character")["DPS"].max().sort_values(ascending=False).reset_index()
        
        with open("Results/max_dps_summary.md", "w", encoding="utf-8") as f:
            f.write("## Character Max DPS (15 Turns)\n\n")
            f.write("| Character | Max DPS |\n")
            f.write("| :--- | :--- |\n")
            for index, row in max_dps.iterrows():
                f.write(f"| {row['Character']} | {row['DPS']:,.2f} |\n")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_dps_gaps()
